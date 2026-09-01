"""
Punto de entrada de la aplicación FastAPI.

Correr en desarrollo:
    uvicorn app.main:app --reload

Documentación interactiva de la API una vez corriendo:
    http://127.0.0.1:8000/docs
"""
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .database import Base, engine
from .routers import events, ingest, pages, patients, summary, trends

# Crea las tablas si no existen (para SQLite/desarrollo; en producción usar
# migraciones con Alembic — ver docs/ARQUITECTURA.md).
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Gestión Salud y Deporte",
    description="Organiza información personal de salud y deporte bajo categorías del estándar HL7 FHIR.",
    version="0.1.0",
)

app.mount(
    "/static",
    StaticFiles(directory=str(Path(__file__).resolve().parent / "static")),
    name="static",
)

app.include_router(patients.router)
app.include_router(events.router)
app.include_router(pages.router)
app.include_router(ingest.router)
app.include_router(summary.router)
app.include_router(trends.router)
