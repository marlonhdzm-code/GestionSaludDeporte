"""
Fixtures compartidas para pruebas que usan TestClient (contra la API/paginas
HTTP reales). Un solo engine/override de get_db para todos los archivos de
prueba que lo necesiten -- si cada archivo de test define el suyo propio,
como app.dependency_overrides[get_db] es un diccionario global sobre la
misma instancia de FastAPI, el ultimo archivo importado "gana" y los demas
terminan corriendo contra la base de datos equivocada.

Los tests que no usan TestClient (por ejemplo test_email_ingest.py, que
llama funciones de app.email_ingest directamente con su propia sesion) no
necesitan estas fixtures.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _override_get_db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db


@pytest.fixture(autouse=True)
def _clean_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture()
def db_session():
    """Una sesion directa contra la misma base de datos que usa TestClient."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
