"""
Ruta de ingesta: subir una foto de un documento de salud, que la IA la lea,
y mostrarle al usuario un formulario prellenado para que confirme antes de
guardar. Nunca se guarda nada automáticamente sin esa confirmación.
"""
import base64

from fastapi import APIRouter, Depends, Request, UploadFile
from fastapi.templating import Jinja2Templates
from pathlib import Path
from sqlalchemy.orm import Session

from .. import config, crud
from ..ai_extract import AIExtractionError, extract_health_event_from_image
from ..database import get_db
from .pages import RESOURCE_LABELS, _current_patient

router = APIRouter(prefix="/importar", include_in_schema=False)
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))


@router.get("")
def importar_form(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(
        request,
        "importar.html",
        {
            "ai_configured": config.AI_CONFIGURED,
            "labels": RESOURCE_LABELS,
            "all_patients": crud.list_patients(db),
        },
    )


@router.post("/analizar")
async def importar_analizar(request: Request, foto: UploadFile, db: Session = Depends(get_db)):
    patient = _current_patient(db, request)
    image_bytes = await foto.read()
    media_type = foto.content_type or "image/jpeg"

    try:
        extracted = extract_health_event_from_image(image_bytes, media_type)
        error = None
    except AIExtractionError as exc:
        extracted = None
        error = str(exc)

    image_data_uri = f"data:{media_type};base64,{base64.standard_b64encode(image_bytes).decode('ascii')}"

    return templates.TemplateResponse(
        request,
        "confirmar_evento.html",
        {
            "patient": patient,
            "labels": RESOURCE_LABELS,
            "extracted": extracted,
            "error": error,
            "image_data_uri": image_data_uri,
            "all_patients": crud.list_patients(db),
        },
    )
