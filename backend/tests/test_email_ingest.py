"""
Pruebas de app.email_ingest.revisar_bandeja_entrada, usando un IMAP falso
(no se conecta a ningun servidor real ni gasta la cuota de la API salvo
donde se indique explicitamente con monkeypatch).
"""
from email.message import EmailMessage

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import config, crud, email_ingest, models, schemas
from app.database import Base
from app.ai_extract import AIExtractionError

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class FakeIMAP:
    def __init__(self, mensajes: dict[bytes, bytes]):
        self.mensajes = mensajes
        self.store_calls: list[tuple] = []

    def select(self, mailbox):
        return "OK", [b"1"]

    def search(self, charset, criteria):
        if self.mensajes:
            return "OK", [b" ".join(self.mensajes.keys())]
        return "OK", [b""]

    def fetch(self, msg_id, parts):
        return "OK", [(None, self.mensajes[msg_id])]

    def store(self, msg_id, flag_cmd, flag):
        self.store_calls.append((msg_id, flag_cmd, flag))
        return "OK", []

    def logout(self):
        pass


@pytest.fixture(autouse=True)
def _clean_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture()
def db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(autouse=True)
def _gmail_configurado(monkeypatch):
    monkeypatch.setattr(config, "GMAIL_ADDRESS", "pasarela@gmail.com")
    monkeypatch.setattr(config, "GMAIL_APP_PASSWORD", "clave-de-aplicacion")
    monkeypatch.setattr(config, "EMAIL_INGEST_CONFIGURED", True)


def _fake_conectar(fake_imap: FakeIMAP):
    def _conectar():
        return fake_imap

    return _conectar


def _crear_paciente(db, email="marlon@hotmail.com"):
    return crud.create_patient(db, schemas.PatientCreate(full_name="Marlon", email=email))


def test_no_configurado_devuelve_error_claro(monkeypatch, db):
    monkeypatch.setattr(config, "EMAIL_INGEST_CONFIGURED", False)
    resultado = email_ingest.revisar_bandeja_entrada(db)
    assert resultado["ok"] is False
    assert "no esta configurada" in resultado["error"] or "no está configurada" in resultado["error"]


def test_remitente_no_reconocido_se_ignora_y_se_marca_leido(monkeypatch, db):
    _crear_paciente(db, email="marlon@hotmail.com")

    msg = EmailMessage()
    msg["From"] = "spam@desconocido.com"
    msg["Subject"] = "Oferta especial"
    msg.set_content("Compra ya con descuento del 50 por ciento, este mensaje no es de salud.")
    fake_imap = FakeIMAP({b"1": msg.as_bytes()})
    monkeypatch.setattr(email_ingest, "_conectar", _fake_conectar(fake_imap))

    resultado = email_ingest.revisar_bandeja_entrada(db)

    assert resultado["ok"] is True
    assert resultado["mensajes_revisados"] == 1
    assert resultado["no_reconocidos"] == 1
    assert resultado["pendientes_nuevos"] == 0
    assert len(crud.list_pending_email_events(db)) == 0
    assert fake_imap.store_calls == [(b"1", "+FLAGS", "\\Seen")]


def test_adjunto_pdf_de_remitente_reconocido_crea_pendiente(monkeypatch, db):
    patient = _crear_paciente(db, email="marlon@hotmail.com")

    msg = EmailMessage()
    msg["From"] = "Marlon <marlon@hotmail.com>"
    msg["Subject"] = "Resultado de laboratorio"
    msg.set_content("Ver adjunto.")
    msg.add_attachment(b"%PDF-contenido-falso", maintype="application", subtype="pdf", filename="resultado.pdf")
    fake_imap = FakeIMAP({b"1": msg.as_bytes()})
    monkeypatch.setattr(email_ingest, "_conectar", _fake_conectar(fake_imap))

    extraido_falso = {
        "resource_type": "Observation",
        "event_date_text": "01/09/2026",
        "event_date_sort": "2026-09-01",
        "title": "Hemoglobina",
        "detail": "",
        "value": "14.5 g/dL",
        "reference_range": "13.5-17",
        "institution": "SURA",
        "notes_for_user": "",
    }
    monkeypatch.setattr(email_ingest, "extract_health_event_from_pdf", lambda pdf_bytes: extraido_falso)
    monkeypatch.setattr(
        email_ingest,
        "extract_health_event_from_email_text",
        lambda subject, body: None,
    )

    resultado = email_ingest.revisar_bandeja_entrada(db)

    assert resultado["ok"] is True
    assert resultado["pendientes_nuevos"] == 1
    pendientes = crud.list_pending_email_events(db, patient_id=patient.id)
    assert len(pendientes) == 1
    assert pendientes[0].preview_type == "pdf"
    assert pendientes[0].error is None


def test_extraccion_fallida_guarda_pendiente_con_error(monkeypatch, db):
    _crear_paciente(db, email="marlon@hotmail.com")

    msg = EmailMessage()
    msg["From"] = "marlon@hotmail.com"
    msg["Subject"] = "Resultado"
    msg.set_content("Ver adjunto.")
    msg.add_attachment(b"%PDF-contenido-falso", maintype="application", subtype="pdf", filename="resultado.pdf")
    fake_imap = FakeIMAP({b"1": msg.as_bytes()})
    monkeypatch.setattr(email_ingest, "_conectar", _fake_conectar(fake_imap))

    def _falla(pdf_bytes):
        raise AIExtractionError("El PDF esta protegido con contrasena.")

    monkeypatch.setattr(email_ingest, "extract_health_event_from_pdf", _falla)
    monkeypatch.setattr(email_ingest, "extract_health_event_from_email_text", lambda subject, body: None)

    resultado = email_ingest.revisar_bandeja_entrada(db)

    assert resultado["pendientes_nuevos"] == 1
    pendiente = crud.list_pending_email_events(db)[0]
    assert pendiente.error == "El PDF esta protegido con contrasena."
    assert pendiente.extracted_json is None


def test_cuerpo_de_texto_relevante_crea_pendiente(monkeypatch, db):
    patient = _crear_paciente(db, email="marlon@hotmail.com")

    msg = EmailMessage()
    msg["From"] = "marlon@hotmail.com"
    msg["Subject"] = "Resultado de hemoglobina"
    msg.set_content("Hemoglobina: 14.5 g/dL (rango 13.5-17). Fecha: 10/02/2026. Laboratorio SURA.")
    fake_imap = FakeIMAP({b"1": msg.as_bytes()})
    monkeypatch.setattr(email_ingest, "_conectar", _fake_conectar(fake_imap))

    extraido_falso = {
        "resource_type": "Observation",
        "event_date_text": "10/02/2026",
        "event_date_sort": "2026-02-10",
        "title": "Hemoglobina",
        "detail": "",
        "value": "14.5 g/dL",
        "reference_range": "13.5-17",
        "institution": "SURA",
        "notes_for_user": "",
    }
    monkeypatch.setattr(email_ingest, "extract_health_event_from_email_text", lambda subject, body: extraido_falso)

    resultado = email_ingest.revisar_bandeja_entrada(db)

    assert resultado["pendientes_nuevos"] == 1
    pendientes = crud.list_pending_email_events(db, patient_id=patient.id)
    assert pendientes[0].preview_type == "texto"


def test_cuerpo_de_texto_no_relevante_no_crea_pendiente(monkeypatch, db):
    _crear_paciente(db, email="marlon@hotmail.com")

    msg = EmailMessage()
    msg["From"] = "marlon@hotmail.com"
    msg["Subject"] = "Fwd: Fwd: Fwd: Resultado"
    msg.set_content("Hola, te reenvio esto, saludos, cuidate mucho, cualquier cosa me escribes.")
    fake_imap = FakeIMAP({b"1": msg.as_bytes()})
    monkeypatch.setattr(email_ingest, "_conectar", _fake_conectar(fake_imap))
    monkeypatch.setattr(email_ingest, "extract_health_event_from_email_text", lambda subject, body: None)

    resultado = email_ingest.revisar_bandeja_entrada(db)

    assert resultado["pendientes_nuevos"] == 0
    assert len(crud.list_pending_email_events(db)) == 0


def test_sin_correos_nuevos(monkeypatch, db):
    fake_imap = FakeIMAP({})
    monkeypatch.setattr(email_ingest, "_conectar", _fake_conectar(fake_imap))

    resultado = email_ingest.revisar_bandeja_entrada(db)

    assert resultado["ok"] is True
    assert resultado["mensajes_revisados"] == 0
    assert resultado["pendientes_nuevos"] == 0
