"""
Extracción de datos de salud a partir de una foto, usando la API de Claude.

En vez de un motor de OCR separado (que requeriría instalar software extra
en Windows), se le manda la imagen directamente a un modelo de Claude con
capacidad de visión, pidiéndole que lea el contenido y lo devuelva ya
estructurado según nuestras categorías FHIR. El resultado SIEMPRE pasa por
una pantalla de confirmación humana antes de guardarse — ver routers/ingest.py.
"""
import json
import re

from . import config
from .models import ResourceType

ALLOWED_MEDIA_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}

RESOURCE_TYPE_GUIDE = """\
- Condition: un diagnóstico, antecedente o hallazgo clínico
- MedicationStatement: un medicamento y su dosis/frecuencia
- Observation: un resultado puntual de laboratorio o un signo vital
- DiagnosticReport: un estudio o procedimiento (ecografía, resonancia, endoscopia...)
- Encounter: una consulta o cita médica
- Immunization: una vacuna aplicada
- Coverage: información de aseguradora, EPS o trámite administrativo"""

PROMPT = f"""Eres un asistente que ayuda a transcribir información de salud desde la foto \
de un documento (un resultado de laboratorio, una orden médica, un carné de vacunación, etc.) \
hacia un registro estructurado. Es MUY importante que seas preciso: nunca inventes, redondees \
ni completes un valor que no puedas leer con claridad en la imagen.

Las categorías disponibles (estándar HL7 FHIR) son:
{RESOURCE_TYPE_GUIDE}

Mira la imagen adjunta y responde ÚNICAMENTE con un objeto JSON (sin texto antes ni después, \
sin bloque de código markdown) con esta forma exacta:

{{
  "resource_type": "una de las 7 categorías de arriba, la que mejor aplique",
  "event_date_text": "la fecha tal como aparece en el documento, como texto (ej. '24/06/2024'); si no se ve ninguna fecha, usa null",
  "event_date_sort": "la misma fecha en formato YYYY-MM-DD si se puede determinar con certeza, si no null",
  "title": "un título corto del evento (ej. 'Colesterol LDL', 'Ecografía renal', 'Valsartán')",
  "detail": "detalle o descripción adicional visible en el documento, o null",
  "value": "el valor o resultado principal tal como aparece (con su unidad), o null",
  "reference_range": "el rango de referencia si aparece en el documento, o null",
  "institution": "la institución, laboratorio o profesional que aparece en el documento, o null",
  "notes_for_user": "una frase corta en español avisando si algo en la imagen no se pudo leer con claridad, o null si todo se leyó bien"
}}

Si la imagen tiene varios resultados (por ejemplo un panel de laboratorio con varios analitos), \
elige el valor más relevante o principal para "title"/"value", y menciona los demás en "detail". \
Si la imagen no parece ser un documento de salud, responde con "resource_type": "Observation" y \
explica la situación en "notes_for_user"."""


class AIExtractionError(Exception):
    """Se lanza cuando la extracción falla o el modelo no está configurado."""


def _client():
    if not config.AI_CONFIGURED:
        raise AIExtractionError(
            "No hay una llave de API de Anthropic configurada. Copia .env.example a .env "
            "en la raíz del proyecto y pega tu llave (ANTHROPIC_API_KEY)."
        )
    try:
        from anthropic import Anthropic
    except ImportError as exc:  # pragma: no cover
        raise AIExtractionError(
            "Falta instalar la librería 'anthropic' (revisa requirements.txt)."
        ) from exc
    extra_headers = {}
    if config.ANTHROPIC_WORKSPACE_ID:
        extra_headers["anthropic-workspace-id"] = config.ANTHROPIC_WORKSPACE_ID
    return Anthropic(api_key=config.ANTHROPIC_API_KEY, default_headers=extra_headers or None)


def _parse_json_response(raw_text: str) -> dict:
    text = raw_text.strip()
    # Por si el modelo igual envuelve la respuesta en ```json ... ``` a pesar de la instrucción.
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise AIExtractionError("La IA no devolvió un JSON reconocible. Intenta de nuevo.")
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise AIExtractionError(f"La respuesta de la IA no es JSON válido: {exc}") from exc


def extract_health_event_from_image(image_bytes: bytes, media_type: str) -> dict:
    """
    Envía la imagen a Claude y devuelve un diccionario con los campos de
    HealthEvent (sin patient_id) listos para prellenar el formulario de
    confirmación. Lanza AIExtractionError si algo falla.
    """
    if media_type not in ALLOWED_MEDIA_TYPES:
        raise AIExtractionError(
            f"Formato de imagen no soportado ({media_type}). Usa JPEG, PNG, WEBP o GIF."
        )
    if len(image_bytes) > 15 * 1024 * 1024:
        raise AIExtractionError("La imagen pesa más de 15 MB — intenta con una foto más liviana.")

    import base64

    client = _client()
    b64_image = base64.standard_b64encode(image_bytes).decode("ascii")

    try:
        response = client.messages.create(
            model=config.ANTHROPIC_MODEL,
            max_tokens=1024,
            temperature=0,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {"type": "base64", "media_type": media_type, "data": b64_image},
                        },
                        {"type": "text", "text": PROMPT},
                    ],
                }
            ],
        )
    except Exception as exc:  # anthropic.APIError y subclases
        raise AIExtractionError(f"No se pudo contactar a la API de Claude: {exc}") from exc

    raw_text = "".join(block.text for block in response.content if getattr(block, "type", None) == "text")
    data = _parse_json_response(raw_text)

    resource_type = data.get("resource_type")
    if resource_type not in [rt.value for rt in ResourceType]:
        data["notes_for_user"] = (
            (data.get("notes_for_user") or "")
            + " La IA no reconoció con certeza la categoría FHIR; revísala manualmente."
        ).strip()
        resource_type = ResourceType.OBSERVATION.value

    return {
        "resource_type": resource_type,
        "event_date_text": data.get("event_date_text") or "",
        "event_date_sort": data.get("event_date_sort") or "",
        "title": data.get("title") or "",
        "detail": data.get("detail") or "",
        "value": data.get("value") or "",
        "reference_range": data.get("reference_range") or "",
        "institution": data.get("institution") or "",
        "notes_for_user": data.get("notes_for_user") or "",
    }
