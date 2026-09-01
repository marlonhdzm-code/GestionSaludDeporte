"""
Fase 3: resumen médico interpretativo con IA, sobre el historial completo
del paciente activo (todas sus categorías FHIR, incluida la "deportiva":
datos de reloj Garmin guardados como Observation).

Igual que la Fase 1 (importar por foto), esto nunca se guarda como un hecho
médico verificado ni se persiste en la base de datos — es una lectura que
se genera al pedirla y se muestra con su evidencia, para que el usuario
decida qué llevarle a su médico. El aviso de que no reemplaza el criterio
médico se muestra siempre, sin importar lo que devuelva el modelo.

Cada hallazgo puede venir acompañado de un "marcador" (el título exacto de
un analito/medición, ej. "Hemoglobina") que la IA identifica como el más
representativo del patrón. Cuando existe y tiene al menos 2 puntos
graficables, se le adjunta su propia mini-gráfica de tendencia (mismo
cálculo que /api/trends/{title} en routers/trends.py), para que el usuario
pueda ver el dato detrás del hallazgo con solo desplegarlo.
"""
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from .. import config, crud
from ..ai_summary import AISummaryError, generate_health_summary
from ..database import get_db
from ..models import HealthEvent
from ..trends import parse_numeric_value, parse_reference_range
from .pages import _current_patient

router = APIRouter(prefix="/resumen", include_in_schema=False)
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))


def _build_chart(events: list[HealthEvent], title: str) -> dict | None:
    """Arma los datos de tendencia para un título de evento (igual criterio que
    /api/trends/{title}): solo se devuelve algo si hay al menos 2 puntos con
    fecha exacta y valor numérico."""
    matching = [e for e in events if e.title == title and e.event_date_sort is not None]
    matching.sort(key=lambda e: e.event_date_sort)

    points = []
    parsed_ranges = []
    for e in matching:
        numeric_value = parse_numeric_value(e.value)
        if numeric_value is None:
            continue
        points.append({
            "date": e.event_date_sort.isoformat(),
            "value": numeric_value,
            "raw_value": e.value,
            "institution": e.institution,
        })
        r = parse_reference_range(e.reference_range)
        if r:
            parsed_ranges.append(r)

    if len(points) < 2:
        return None

    return {
        "title": title,
        "points": points,
        "reference_range": parsed_ranges[-1] if parsed_ranges else None,
    }


def _attach_charts(result: dict, events: list[HealthEvent]) -> None:
    """Le agrega result['hallazgos'][i]['chart'] a cada hallazgo que traiga un
    'marcador' graficable. Modifica result en el lugar."""
    chart_cache: dict[str, dict | None] = {}
    for h in result.get("hallazgos", []):
        marcador = h.get("marcador")
        chart = None
        if marcador:
            if marcador not in chart_cache:
                chart_cache[marcador] = _build_chart(events, marcador)
            chart = chart_cache[marcador]
        h["chart"] = chart


@router.get("")
def resumen_form(request: Request, db: Session = Depends(get_db)):
    patient = _current_patient(db, request)
    event_count = len(crud.list_events(db, patient_id=patient.id)) if patient else 0
    return templates.TemplateResponse(
        request,
        "resumen.html",
        {
            "patient": patient,
            "ai_configured": config.AI_CONFIGURED,
            "all_patients": crud.list_patients(db),
            "result": None,
            "error": None,
            "event_count": event_count,
        },
    )


@router.post("/generar")
def resumen_generar(request: Request, db: Session = Depends(get_db)):
    patient = _current_patient(db, request)
    events = crud.list_events(db, patient_id=patient.id) if patient else []

    result = None
    error = None
    try:
        result = generate_health_summary(patient, events)
        _attach_charts(result, events)
    except AISummaryError as exc:
        error = str(exc)

    return templates.TemplateResponse(
        request,
        "resumen.html",
        {
            "patient": patient,
            "ai_configured": config.AI_CONFIGURED,
            "all_patients": crud.list_patients(db),
            "result": result,
            "error": error,
            "event_count": len(events),
        },
    )
