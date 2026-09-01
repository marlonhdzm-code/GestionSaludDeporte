"""Pruebas de las rutas /correo (bandeja, registrar email, confirmar, descartar)."""
import json

from app import crud, schemas

from .conftest import TestingSessionLocal


def _crear_paciente_activo():
    db = TestingSessionLocal()
    try:
        return crud.create_patient(db, schemas.PatientCreate(full_name="Marlon"))
    finally:
        db.close()


def test_bandeja_correo_carga_sin_configurar(client):
    _crear_paciente_activo()
    resp = client.get("/correo")
    assert resp.status_code == 200
    assert "todav" in resp.text  # aviso de "todavía no está configurada"


def test_registrar_email_guarda_en_paciente_activo(client):
    patient = _crear_paciente_activo()
    resp = client.post(
        "/correo/registrar-email",
        data={"correo_autorizado": "marlon@hotmail.com"},
        follow_redirects=False,
    )
    assert resp.status_code == 303

    db = TestingSessionLocal()
    try:
        actualizado = crud.get_patient(db, patient.id)
        assert actualizado.email == "marlon@hotmail.com"
    finally:
        db.close()


def test_confirmar_pendiente_crea_evento_y_borra_pendiente(client):
    patient = _crear_paciente_activo()
    db = TestingSessionLocal()
    try:
        pendiente = crud.create_pending_email_event(
            db,
            patient_id=patient.id,
            email_subject="Resultado",
            email_from="marlon@hotmail.com",
            email_date="",
            preview_type="texto",
            preview_content="Hemoglobina 14.5",
            preview_media_type=None,
            extracted_json=json.dumps(
                {
                    "resource_type": "Observation",
                    "event_date_text": "01/09/2026",
                    "event_date_sort": "2026-09-01",
                    "title": "Hemoglobina",
                    "detail": "",
                    "value": "14.5 g/dL",
                    "reference_range": "",
                    "institution": "",
                    "notes_for_user": "",
                }
            ),
            error=None,
        )
        pending_id = pendiente.id
    finally:
        db.close()

    resp = client.get(f"/correo/{pending_id}")
    assert resp.status_code == 200
    assert "Hemoglobina" in resp.text

    resp = client.post(
        f"/correo/{pending_id}/confirmar",
        data={
            "resource_type": "Observation",
            "event_date_text": "01/09/2026",
            "event_date_sort": "2026-09-01",
            "title": "Hemoglobina",
            "value": "14.5 g/dL",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 303

    db = TestingSessionLocal()
    try:
        assert crud.get_pending_email_event(db, pending_id) is None
        eventos = crud.list_events(db, patient_id=patient.id)
        assert len(eventos) == 1
        assert eventos[0].title == "Hemoglobina"
    finally:
        db.close()


def test_reintentar_pdf_con_contrasena_correcta_actualiza_pendiente(client, monkeypatch):
    import base64

    patient = _crear_paciente_activo()
    db = TestingSessionLocal()
    try:
        pendiente = crud.create_pending_email_event(
            db,
            patient_id=patient.id,
            email_subject="Resultado",
            email_from="marlon@hotmail.com",
            email_date="",
            preview_type="pdf",
            preview_content=base64.standard_b64encode(b"%PDF-falso").decode("ascii"),
            preview_media_type="application/pdf",
            extracted_json=None,
            error="Este PDF está protegido con contraseña. Ingrésala en el campo de abajo.",
        )
        pending_id = pendiente.id
    finally:
        db.close()

    extraido_falso = {
        "resource_type": "Observation",
        "event_date_text": "01/09/2026",
        "event_date_sort": "2026-09-01",
        "title": "Hemoglobina",
        "detail": "",
        "value": "14.5 g/dL",
        "reference_range": "",
        "institution": "",
        "notes_for_user": "",
    }

    def fake_extract(pdf_bytes, password=None):
        assert password == "1234567890"
        return extraido_falso

    import app.routers.correo as correo_module

    monkeypatch.setattr(correo_module, "extract_health_event_from_pdf", fake_extract)

    resp = client.post(
        f"/correo/{pending_id}/reintentar-pdf",
        data={"contrasena": "1234567890"},
        follow_redirects=False,
    )
    assert resp.status_code == 303

    db = TestingSessionLocal()
    try:
        actualizado = crud.get_pending_email_event(db, pending_id)
        assert actualizado.error is None
        assert "Hemoglobina" in actualizado.extracted_json
    finally:
        db.close()


def test_reintentar_pdf_con_contrasena_incorrecta_mantiene_error(client, monkeypatch):
    import base64

    from app.ai_extract import AIExtractionError

    patient = _crear_paciente_activo()
    db = TestingSessionLocal()
    try:
        pendiente = crud.create_pending_email_event(
            db,
            patient_id=patient.id,
            email_subject="Resultado",
            email_from="marlon@hotmail.com",
            email_date="",
            preview_type="pdf",
            preview_content=base64.standard_b64encode(b"%PDF-falso").decode("ascii"),
            preview_media_type="application/pdf",
            extracted_json=None,
            error="Este PDF está protegido con contraseña. Ingrésala en el campo de abajo.",
        )
        pending_id = pendiente.id
    finally:
        db.close()

    def fake_extract(pdf_bytes, password=None):
        raise AIExtractionError("La contraseña que ingresaste no es correcta para este PDF.")

    import app.routers.correo as correo_module

    monkeypatch.setattr(correo_module, "extract_health_event_from_pdf", fake_extract)

    resp = client.post(
        f"/correo/{pending_id}/reintentar-pdf",
        data={"contrasena": "clave-mala"},
        follow_redirects=False,
    )
    assert resp.status_code == 303

    db = TestingSessionLocal()
    try:
        actualizado = crud.get_pending_email_event(db, pending_id)
        assert actualizado.extracted_json is None
        assert "no es correcta" in actualizado.error
    finally:
        db.close()


def test_descartar_pendiente_lo_elimina_sin_crear_evento(client):
    patient = _crear_paciente_activo()
    db = TestingSessionLocal()
    try:
        pendiente = crud.create_pending_email_event(
            db,
            patient_id=patient.id,
            email_subject="Oferta",
            email_from="spam@x.com",
            email_date="",
            preview_type="texto",
            preview_content="no relevante",
            preview_media_type=None,
            extracted_json=None,
            error="No se pudo analizar.",
        )
        pending_id = pendiente.id
    finally:
        db.close()

    resp = client.post(f"/correo/{pending_id}/descartar", follow_redirects=False)
    assert resp.status_code == 303

    db = TestingSessionLocal()
    try:
        assert crud.get_pending_email_event(db, pending_id) is None
        assert len(crud.list_events(db, patient_id=patient.id)) == 0
    finally:
        db.close()
