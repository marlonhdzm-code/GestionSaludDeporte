"""Rutas que renderizan páginas HTML (interfaz web), separadas de la API JSON."""
from datetime import date

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..database import get_db
from pathlib import Path

router = APIRouter(include_in_schema=False)
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))

RESOURCE_LABELS = {
    "Condition": "Antecedentes y diagnósticos",
    "MedicationStatement": "Medicación",
    "Observation": "Resultados de laboratorio",
    "DiagnosticReport": "Imágenes y procedimientos",
    "Encounter": "Consultas y citas",
    "Immunization": "Vacunación",
    "Coverage": "Aseguramiento en salud",
}

ACTIVE_PATIENT_COOKIE = "active_patient_id"


def _current_patient(db: Session, request: Request | None = None) -> models.Patient | None:
    """Paciente activo.

    La app todavía no tiene autenticación real (eso es la Fase 4,
    multiusuario). Mientras tanto, esto es un selector liviano entre los
    pacientes que existan en esta base de datos (por ejemplo, tus datos
    reales y un paciente de prueba como Greg Welch), recordado en una
    cookie. Si no hay cookie o no coincide con ningún paciente, se usa el
    primero que exista.
    """
    patients = crud.list_patients(db)
    if not patients:
        return None
    if request is not None:
        cookie_value = request.cookies.get(ACTIVE_PATIENT_COOKIE)
        if cookie_value:
            try:
                cookie_id = int(cookie_value)
            except ValueError:
                cookie_id = None
            if cookie_id is not None:
                match = next((p for p in patients if p.id == cookie_id), None)
                if match is not None:
                    return match
    return patients[0]


def _selector_context(db: Session) -> dict:
    """Contexto común para que base.html pueda mostrar el selector de paciente."""
    return {"all_patients": crud.list_patients(db)}


@router.post("/paciente/activar")
def paciente_activar(request: Request, patient_id: int = Form(...)):
    redirect_to = request.headers.get("referer", "/")
    response = RedirectResponse(url=redirect_to, status_code=303)
    response.set_cookie(ACTIVE_PATIENT_COOKIE, str(patient_id), max_age=60 * 60 * 24 * 365)
    return response


@router.get("/")
def dashboard(request: Request, db: Session = Depends(get_db)):
    patient = _current_patient(db, request)
    counts = crud.counts_by_category(db, patient.id) if patient else {}
    recent = crud.list_events(db, patient_id=patient.id)[-8:][::-1] if patient else []
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "patient": patient,
            "counts": counts,
            "labels": RESOURCE_LABELS,
            "recent": recent,
            **_selector_context(db),
        },
    )


@router.get("/eventos")
def eventos(request: Request, categoria: str | None = None, db: Session = Depends(get_db)):
    patient = _current_patient(db, request)
    resource_type = models.ResourceType(categoria) if categoria else None
    events = crud.list_events(db, patient_id=patient.id if patient else None, resource_type=resource_type)
    return templates.TemplateResponse(
        request,
        "eventos.html",
        {
            "patient": patient,
            "events": events,
            "labels": RESOURCE_LABELS,
            "categoria_activa": categoria,
            **_selector_context(db),
        },
    )


@router.get("/eventos/nuevo")
def evento_nuevo_form(request: Request, db: Session = Depends(get_db)):
    patient = _current_patient(db, request)
    return templates.TemplateResponse(
        request,
        "evento_form.html",
        {"patient": patient, "labels": RESOURCE_LABELS, **_selector_context(db)},
    )


@router.post("/eventos/nuevo")
def evento_nuevo_submit(
    request: Request,
    resource_type: str = Form(...),
    event_date_text: str = Form(...),
    event_date_sort: str = Form(""),
    title: str = Form(...),
    detail: str = Form(""),
    value: str = Form(""),
    reference_range: str = Form(""),
    institution: str = Form(""),
    source: str = Form(""),
    db: Session = Depends(get_db),
):
    patient = _current_patient(db, request)
    if patient is None:
        patient = crud.create_patient(db, schemas.PatientCreate(full_name="Paciente"))

    parsed_date: date | None = None
    if event_date_sort:
        try:
            parsed_date = date.fromisoformat(event_date_sort)
        except ValueError:
            parsed_date = None

    event = schemas.HealthEventCreate(
        patient_id=patient.id,
        resource_type=models.ResourceType(resource_type),
        event_date_text=event_date_text,
        event_date_sort=parsed_date,
        title=title,
        detail=detail or None,
        value=value or None,
        reference_range=reference_range or None,
        institution=institution or None,
        source=source or None,
    )
    crud.create_event(db, event)
    return RedirectResponse(url="/eventos", status_code=303)
