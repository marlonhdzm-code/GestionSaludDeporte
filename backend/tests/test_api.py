"""
Pruebas básicas de la API. Usan una base de datos SQLite en memoria distinta
a la de desarrollo, así que correr los tests nunca toca salud_deporte.db.

Correr con:
    cd backend
    pytest
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app

# StaticPool: una sola conexión compartida para toda la vida del engine. Sin esto,
# cada sesión abre una conexión SQLite ":memory:" nueva (es decir, una base vacía
# distinta), y los datos creados en un request desaparecen para el siguiente.
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(autouse=True)
def _clean_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


def test_create_and_list_patient():
    resp = client.post("/api/patients", json={"full_name": "Paciente de Prueba"})
    assert resp.status_code == 201
    patient = resp.json()
    assert patient["full_name"] == "Paciente de Prueba"

    resp = client.get("/api/patients")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_create_event_requires_existing_patient():
    resp = client.post(
        "/api/events",
        json={
            "patient_id": 999,
            "resource_type": "Observation",
            "event_date_text": "01/01/2026",
            "title": "Glucosa",
            "value": "90 mg/dL",
        },
    )
    assert resp.status_code == 404


def test_create_and_filter_events():
    patient = client.post("/api/patients", json={"full_name": "Paciente de Prueba"}).json()

    client.post(
        "/api/events",
        json={
            "patient_id": patient["id"],
            "resource_type": "Observation",
            "event_date_text": "01/01/2026",
            "title": "Glucosa",
            "value": "90 mg/dL",
        },
    )
    client.post(
        "/api/events",
        json={
            "patient_id": patient["id"],
            "resource_type": "Condition",
            "event_date_text": "01/01/2026",
            "title": "Hipertensión",
        },
    )

    resp = client.get(f"/api/events?patient_id={patient['id']}")
    assert resp.status_code == 200
    assert len(resp.json()) == 2

    resp = client.get(f"/api/events?patient_id={patient['id']}&resource_type=Observation")
    assert resp.status_code == 200
    events = resp.json()
    assert len(events) == 1
    assert events[0]["title"] == "Glucosa"


def test_dashboard_page_loads():
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Gesti" in resp.text  # "Gestión..." (evita líos de encoding en el assert)


def test_eventos_page_loads():
    resp = client.get("/eventos")
    assert resp.status_code == 200


def test_importar_page_loads():
    resp = client.get("/importar")
    assert resp.status_code == 200


def test_importar_analizar_shows_friendly_error_without_api_key(monkeypatch):
    """Sin ANTHROPIC_API_KEY configurada, el flujo no debe romperse — debe
    mostrar el mensaje de error dentro de la página de confirmación."""
    monkeypatch.setattr("app.config.AI_CONFIGURED", False)
    resp = client.post(
        "/importar/analizar",
        files={"documento": ("test.jpg", b"\xff\xd8\xff\xe0fake-jpeg-bytes", "image/jpeg")},
    )
    assert resp.status_code == 200
    assert "No se pudo analizar" in resp.text


def test_importar_analizar_prefills_confirmation_form(monkeypatch):
    """Con la extracción simulada (sin llamar a la API real), la página de
    confirmación debe traer los campos ya prellenados."""

    def fake_extract(image_bytes, media_type):
        return {
            "resource_type": "Observation",
            "event_date_text": "15/03/2026",
            "event_date_sort": "2026-03-15",
            "title": "Glucosa en ayunas",
            "detail": "",
            "value": "92 mg/dL",
            "reference_range": "60 - 100",
            "institution": "Laboratorio Clínico",
            "notes_for_user": "",
        }

    monkeypatch.setattr("app.routers.ingest.extract_health_event_from_image", fake_extract)

    resp = client.post(
        "/importar/analizar",
        files={"documento": ("test.jpg", b"\xff\xd8\xff\xe0fake-jpeg-bytes", "image/jpeg")},
    )
    assert resp.status_code == 200
    assert "Glucosa en ayunas" in resp.text
    assert "92 mg/dL" in resp.text
    assert 'action="/eventos/nuevo"' in resp.text


def test_importar_analizar_pdf_uses_pdf_extractor(monkeypatch):
    """Un archivo con content-type application/pdf debe pasar por el
    extractor de PDF, no por el de imagen, y prellenar el formulario igual."""

    def fake_extract_pdf(pdf_bytes):
        return {
            "resource_type": "Observation",
            "event_date_text": "10/02/2026",
            "event_date_sort": "2026-02-10",
            "title": "Hemoglobina",
            "detail": "",
            "value": "14.5 g/dL",
            "reference_range": "13.5 - 17",
            "institution": "Laboratorio SURA",
            "notes_for_user": "",
        }

    def fail_if_called(*args, **kwargs):
        raise AssertionError("no debería llamarse al extractor de imagen para un PDF")

    monkeypatch.setattr("app.routers.ingest.extract_health_event_from_pdf", fake_extract_pdf)
    monkeypatch.setattr("app.routers.ingest.extract_health_event_from_image", fail_if_called)

    resp = client.post(
        "/importar/analizar",
        files={"documento": ("resultado.pdf", b"%PDF-1.4 fake-pdf-bytes", "application/pdf")},
    )
    assert resp.status_code == 200
    assert "Hemoglobina" in resp.text
    assert "PDF analizado con IA" in resp.text


def test_importar_analizar_pdf_without_text_shows_friendly_error(monkeypatch):
    """Un PDF sin texto extraíble (escaneado) debe dar un mensaje de error
    claro en vez de fallar feo."""
    monkeypatch.setattr("app.config.AI_CONFIGURED", True)

    def fake_extract_pdf_scanned(pdf_bytes):
        from app.ai_extract import AIExtractionError

        raise AIExtractionError(
            "Este PDF no tiene texto que se pueda extraer (probablemente es un escaneo)."
        )

    monkeypatch.setattr("app.routers.ingest.extract_health_event_from_pdf", fake_extract_pdf_scanned)

    resp = client.post(
        "/importar/analizar",
        files={"documento": ("escaneo.pdf", b"%PDF-1.4 fake-scanned", "application/pdf")},
    )
    assert resp.status_code == 200
    assert "no tiene texto que se pueda extraer" in resp.text


def test_tendencias_page_loads_with_no_data():
    resp = client.get("/tendencias")
    assert resp.status_code == 200
    assert "suficientes datos" in resp.text


def test_trend_data_endpoint_returns_points_in_chronological_order():
    patient = client.post("/api/patients", json={"full_name": "Paciente de Prueba"}).json()

    # Un evento sin fecha exacta no debe aparecer en la gráfica.
    client.post(
        "/api/events",
        json={
            "patient_id": patient["id"],
            "resource_type": "Observation",
            "event_date_text": "jun-2023",
            "title": "Colesterol total",
            "value": "300 mg/dL",
        },
    )
    client.post(
        "/api/events",
        json={
            "patient_id": patient["id"],
            "resource_type": "Observation",
            "event_date_text": "24/06/2024",
            "event_date_sort": "2024-06-24",
            "title": "Colesterol total",
            "value": "265 mg/dL",
            "reference_range": "0 - 200 (óptimo)",
        },
    )
    client.post(
        "/api/events",
        json={
            "patient_id": patient["id"],
            "resource_type": "Observation",
            "event_date_text": "24/08/2026",
            "event_date_sort": "2026-08-24",
            "title": "Colesterol total",
            "value": "137 mg/dL",
        },
    )

    resp = client.get("/tendencias")
    assert resp.status_code == 200
    assert "Colesterol total" in resp.text

    resp = client.get("/api/trends/Colesterol total")
    assert resp.status_code == 200
    data = resp.json()
    # Solo los 2 eventos CON fecha exacta entran a la gráfica.
    assert [p["date"] for p in data["points"]] == ["2024-06-24", "2026-08-24"]
    assert data["points"][0]["value"] == 265.0
    assert data["points"][1]["value"] == 137.0
    assert data["reference_range"] == [0.0, 200.0]
