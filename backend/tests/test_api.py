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
        files={"foto": ("test.jpg", b"\xff\xd8\xff\xe0fake-jpeg-bytes", "image/jpeg")},
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
        files={"foto": ("test.jpg", b"\xff\xd8\xff\xe0fake-jpeg-bytes", "image/jpeg")},
    )
    assert resp.status_code == 200
    assert "Glucosa en ayunas" in resp.text
    assert "92 mg/dL" in resp.text
    assert 'action="/eventos/nuevo"' in resp.text
