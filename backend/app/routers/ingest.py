"""
Ruta de ingesta: subir una foto de un documento de salud, que la IA la lea,
y mostrarle al usuario un formulario prellenado para que confirme antes de
guardar. Nunca se guarda nada automáticamente sin esa confirmación.
"""
import base64

from fastapi import APIRouter, Depends, Form, Request, UploadFile
from fastapi.templating import Jinja2Templates
from pathlib import Path
from sqlalchemy.orm import Session

from .. import config, crud
from ..ai_extract import AIExtractionError, extract_health_event_from_image, extract_health_event_from_pdf
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
async def importar_analizar(
    request: Request,
    documento: UploadFile,
    contrasena: str = Form(""),
    db: Session = Depends(get_db),
):
    patient = _current_patient(db, request)
    file_bytes = await documento.read()
    media_type = documento.content_type or "image/jpeg"
    filename = documento.filename or ""
    is_pdf = media_type == "application/pdf" or filename.lower().endswith(".pdf")

    try:
        if is_pdf:
            extracted = extract_health_event_from_pdf(file_bytes, password=contrasena or None)
        else:
            extracted = extract_health_event_from_image(file_bytes, media_type)
        error = None
    except AIExtractionError as exc:
        extracted = None
        error = str(exc)

    if is_pdf:
        preview_type = "pdf"
        preview_data_uri = f"data:application/pdf;base64,{base64.standard_b64encode(file_bytes).decode('ascii')}"
        default_source = "PDF analizado con IA — confirmado por el paciente"
    else:
        preview_type = "image"
        preview_data_uri = f"data:{media_type};base64,{base64.standard_b64encode(file_bytes).decode('ascii')}"
        default_source = "Foto analizada con IA — confirmado por el paciente"

    return templates.TemplateResponse(
        request,
        "confirmar_evento.html",
        {
            "patient": patient,
            "labels": RESOURCE_LABELS,
            "extracted": extracted,
            "error": error,
            "preview_type": preview_type,
            "preview_data_uri": preview_data_uri,
            "default_source": default_source,
            "all_patients": crud.list_patients(db),
        },
    )
