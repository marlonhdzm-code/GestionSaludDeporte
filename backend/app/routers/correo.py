"""
Bandeja de correo: reenviar un correo del laboratorio/EPS a la direccion
pasarela de Gmail, revisar lo que llego, y confirmar (o descartar) cada
candidato antes de que se convierta en un HealthEvent real.

Ningun dato entra a la base de datos "de una" -- ver email_ingest.py y
docs/ARQUITECTURA.md (seccion "Ingesta por correo / reenvio").
"""
import json
from datetime import date
from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from .. import config, crud, schemas
from ..database import get_db
from ..email_ingest import revisar_bandeja_entrada
from .pages import RESOURCE_LABELS, _current_patient, _selector_context

router = APIRouter(prefix="/correo", include_in_schema=False)
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))


@router.get("")
def correo_bandeja(request: Request, revisado: str | None = None, db: Session = Depends(get_db)):
    patient = _current_patient(db, request)
    pendientes_db = crud.list_pending_email_events(db, patient_id=patient.id if patient else None)
    pendientes = []
    for p in pendientes_db:
        extraido = json.loads(p.extracted_json) if p.extracted_json else None
        pendientes.append({"item": p, "extraido": extraido})

    resumen = None
    if revisado:
        resumen = {
            "ok": request.query_params.get("ok") == "1",
            "error": request.query_params.get("error") or None,
            "mensajes_revisados": request.query_params.get("mensajes_revisados"),
            "pendientes_nuevos": request.query_params.get("pendientes_nuevos"),
            "no_reconocidos": request.query_params.get("no_reconocidos"),
        }

    return templates.TemplateResponse(
        request,
        "correo.html",
        {
            "patient": patient,
            "pendientes": pendientes,
            "resumen": resumen,
            "email_ingest_configured": config.EMAIL_INGEST_CONFIGURED,
            "gmail_address": config.GMAIL_ADDRESS,
            "email_poll_minutes": config.EMAIL_POLL_MINUTES,
            **_selector_context(db),
        },
    )


@router.post("/registrar-email")
def correo_registrar_email(request: Request, correo_autorizado: str = Form(...), db: Session = Depends(get_db)):
    patient = _current_patient(db, request)
    if patient is not None:
        crud.update_patient_email(db, patient.id, correo_autorizado.strip())
    return RedirectResponse(url="/correo", status_code=303)


@router.post("/revisar")
def correo_revisar(db: Session = Depends(get_db)):
    resultado = revisar_bandeja_entrada(db)
    params = {"revisado": "1", "ok": "1" if resultado.get("ok") else "0"}
    if resultado.get("ok"):
        params["mensajes_revisados"] = str(resultado.get("mensajes_revisados", 0))
        params["pendientes_nuevos"] = str(resultado.get("pendientes_nuevos", 0))
        params["no_reconocidos"] = str(resultado.get("no_reconocidos", 0))
    else:
        params["error"] = resultado.get("error") or "Error desconocido."
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return RedirectResponse(url=f"/correo?{query}", status_code=303)


@router.get("/{pending_id}")
def correo_ver_pendiente(pending_id: int, request: Request, db: Session = Depends(get_db)):
    pendiente = crud.get_pending_email_event(db, pending_id)
    if pendiente is None:
        return RedirectResponse(url="/correo", status_code=303)
    extraido = json.loads(pendiente.extracted_json) if pendiente.extracted_json else None
    return templates.TemplateResponse(
        request,
        "confirmar_pendiente.html",
        {
            "patient": pendiente.patient,
            "labels": RESOURCE_LABELS,
            "pendiente": pendiente,
            "extraido": extraido,
            **_selector_context(db),
        },
    )


@router.post("/{pending_id}/confirmar")
def correo_confirmar_pendiente(
    pending_id: int,
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
    pendiente = crud.get_pending_email_event(db, pending_id)
    if pendiente is None:
        return RedirectResponse(url="/correo", status_code=303)

    parsed_date: date | None = None
    if event_date_sort:
        try:
            parsed_date = date.fromisoformat(event_date_sort)
        except ValueError:
            parsed_date = None

    from .. import models

    event = schemas.HealthEventCreate(
        patient_id=pendiente.patient_id,
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
    crud.delete_pending_email_event(db, pending_id)
    return RedirectResponse(url="/correo", status_code=303)


@router.post("/{pending_id}/descartar")
def correo_descartar_pendiente(pending_id: int, db: Session = Depends(get_db)):
    crud.delete_pending_email_event(db, pending_id)
    return RedirectResponse(url="/correo", status_code=303)
