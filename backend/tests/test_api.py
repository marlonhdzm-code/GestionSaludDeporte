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
