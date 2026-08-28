"""
Fase 2: tendencias en el tiempo. Una página que grafica la evolución de un
analito (por título de HealthEvent), con el rango de referencia como banda
de fondo cuando se puede interpretar.
"""
from collections import defaultdict
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from .. import crud
from ..database import get_db
from ..trends import parse_numeric_value, parse_reference_range
from .pages import _current_patient

router = APIRouter(include_in_schema=False)
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))


def _chartable_titles(db: Session, patient_id: int) -> list[str]:
    """Títulos con al menos 2 eventos que tienen fecha exacta y valor numérico."""
    counts: dict[str, int] = defaultdict(int)
    for e in crud.list_events(db, patient_id=patient_id):
        if e.event_date_sort is None:
            continue
        if parse_numeric_value(e.value) is None:
            continue
        counts[e.title] += 1
    return sorted(title for title, n in counts.items() if n >= 2)


@router.get("/tendencias")
def tendencias_page(request: Request, titulo: str | None = None, db: Session = Depends(get_db)):
    patient = _current_patient(db)
    titles = _chartable_titles(db, patient.id) if patient else []
    selected = titulo if titulo in titles else (titles[0] if titles else None)
    return templates.TemplateResponse(
        request,
        "tendencias.html",
        {"patient": patient, "titles": titles, "selected": selected},
    )


@router.get("/api/trends/{title}", include_in_schema=True)
def trend_data(title: str, db: Session = Depends(get_db)):
    """JSON consumido por Chart.js en /tendencias — no requiere patient_id
    porque, igual que el resto de la interfaz web, esta app maneja un solo
    paciente activo (ver _current_patient); en la Fase 4 (multiusuario) esto
    pasa a filtrar por el usuario autenticado."""
    patient = _current_patient(db)
    if patient is None:
        raise HTTPException(status_code=404, detail="No hay ningún paciente cargado todavía")

    events = [
        e
        for e in crud.list_events(db, patient_id=patient.id)
        if e.title == title and e.event_date_sort is not None
    ]
    events.sort(key=lambda e: e.event_date_sort)

    points = []
    parsed_ranges = []
    for e in events:
        numeric_value = parse_numeric_value(e.value)
        if numeric_value is None:
            continue
        points.append(
            {
                "date": e.event_date_sort.isoformat(),
                "value": numeric_value,
                "raw_value": e.value,
                "reference_range": e.reference_range,
                "institution": e.institution,
            }
        )
        r = parse_reference_range(e.reference_range)
        if r:
            parsed_ranges.append(r)

    return {
        "title": title,
        "points": points,
        # se usa el rango de referencia interpretado más reciente, si hay alguno
        "reference_range": parsed_ranges[-1] if parsed_ranges else None,
    }
