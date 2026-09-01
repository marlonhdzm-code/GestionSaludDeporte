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

from . import config
from .database import Base, SessionLocal, engine
from .routers import correo, events, ingest, pages, patients, summary, trends

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
app.include_router(correo.router)


def _revisar_correo_en_segundo_plano() -> None:
    """Job periodico: revisa la bandeja de Gmail pasarela con su propia sesion de BD."""
    from .email_ingest import revisar_bandeja_entrada

    db = SessionLocal()
    try:
        revisar_bandeja_entrada(db)
    finally:
        db.close()


@app.on_event("startup")
def _iniciar_revision_periodica_de_correo() -> None:
    """
    Si la bandeja pasarela esta configurada (GMAIL_ADDRESS/GMAIL_APP_PASSWORD en
    .env), arranca un job en segundo plano que la revisa cada
    EMAIL_POLL_MINUTES minutos -- ademas del boton "Revisar ahora" en /correo.
    """
    if not config.EMAIL_INGEST_CONFIGURED:
        return
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
    except ImportError:  # pragma: no cover
        return

    scheduler = BackgroundScheduler()
    scheduler.add_job(
        _revisar_correo_en_segundo_plano,
        "interval",
        minutes=config.EMAIL_POLL_MINUTES,
        id="revisar_correo_pasarela",
        replace_existing=True,
    )
    scheduler.start()
    app.state.email_scheduler = scheduler
