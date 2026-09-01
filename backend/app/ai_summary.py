"""
Fase 3: resumen médico interpretativo con IA.

A diferencia de la Fase 1 (que solo transcribe lo que ve en una foto), acá
se le manda a Claude el historial completo del paciente activo (todos sus
`HealthEvent`, ya organizados por categoría FHIR) y se le pide que busque
patrones y tendencias -- cosas que a simple vista, mirando decenas o
cientos de registros sueltos, son difíciles de notar. El resultado NUNCA
se guarda como si fuera un hecho médico verificado: es una lectura
interpretativa, con la evidencia (fechas/valores) que la respalda, para que
el usuario decida qué vale la pena llevarle a su médico.

Aviso obligatorio: esto no reemplaza el criterio médico. La plantilla
(templates/resumen.html) siempre muestra el aviso, independientemente de lo
que devuelva el modelo.
"""
import json
import re
from collections import defaultdict
from datetime import date

from . import config
from .models import HealthEvent

RESOURCE_LABELS_ES = {
    "Condition": "Antecedentes y diagnósticos",
    "MedicationStatement": "Medicación",
    "Observation": "Resultados de laboratorio / signos vitales / datos de reloj deportivo",
    "DiagnosticReport": "Imágenes y procedimientos",
    "Encounter": "Consultas y citas",
    "Immunization": "Vacunación",
    "Coverage": "Aseguramiento en salud",
}

PROMPT_INSTRUCTIONS = """Eres un asistente que ayuda a leer un historial personal de salud y \
deporte (organizado bajo categorías del estándar HL7 FHIR) para encontrar patrones que a simple \
vista, mirando decenas o cientos de registros sueltos, son difíciles de notar. Esto incluye tanto \
resultados de laboratorio/signos vitales como datos de un reloj deportivo tipo Garmin (VO2max, \
frecuencia cardíaca en reposo, variabilidad de frecuencia cardíaca/HRV, horas de entrenamiento, \
sueño, peso).

Instrucciones importantes:
- Busca TENDENCIAS a lo largo del tiempo (no solo valores puntuales fuera de rango): ¿algo sube, \
baja, o cambia de patrón en un período específico?
- CRUZA datos de distintas categorías cuando tenga sentido clínico o deportivo: por ejemplo, una \
caída de HRV junto con una subida de frecuencia cardíaca en reposo y una carga de entrenamiento \
que se mantiene alta puede sugerir sobreentrenamiento; una caída brusca y sostenida de horas de \
entrenamiento sin explicación puede sugerir una lesión; un marcador de laboratorio que empeora \
progresivamente merece mención aunque cada valor individual esté cerca del rango normal.
- Cada hallazgo debe venir con evidencia concreta: qué datos (con fecha y valor) lo sustentan.
- No inventes datos que no estén en el historial. Si algo no se puede determinar con los datos \
disponibles, no lo afirmes.
- Nunca uses lenguaje de diagnóstico definitivo ("tiene X enfermedad"); usa lenguaje de hallazgo \
o patrón que amerita atención ("los datos muestran un patrón consistente con...", "vale la pena \
comentarle a su médico sobre...").
- Responde ÚNICAMENTE con un objeto JSON (sin texto antes ni después, sin bloque de código \
markdown) con esta forma exacta:

{
  "resumen_general": "2-4 frases con la impresión general del historial (estado, tendencias más notables)",
  "hallazgos": [
    {
      "titulo": "título corto del hallazgo/patrón",
      "categoria": "salud" o "deportivo",
      "nivel": "importante", "atencion", o "informativo" (según qué tan urgente amerita revisión),
      "detalle": "explicación del patrón detectado",
      "evidencia": "los datos concretos (fechas y valores) que sustentan el hallazgo",
      "marcador": "el título EXACTO (copiado tal cual aparece en el historial, ej. 'Hemoglobina' o 'Frecuencia cardíaca en reposo (Garmin)') de UN marcador/medición que mejor represente este hallazgo y se pueda graficar, o null si el hallazgo no corresponde a un solo marcador graficable (ej. una condición, una medicación, o algo que combina varios marcadores a la vez)"
    }
  ],
  "sugerencias": ["sugerencias generales de bienestar/entrenamiento/seguimiento, en lenguaje no prescriptivo, una por elemento"],
  "temas_para_el_medico": ["lista corta de temas puntuales que vale la pena comentarle al médico tratante, si los hay"]
}

Incluye tantos hallazgos como el historial realmente sustente (puede ser ninguno si todo se ve \
normal, o varios) -- no rellenes con hallazgos triviales solo para tener más."""


class AISummaryError(Exception):
    """Se lanza cuando la generación del resumen falla o la IA no está configurada."""


def _client():
    if not config.AI_CONFIGURED:
        raise AISummaryError(
            "No hay una llave de API de Anthropic configurada. Copia .env.example a .env "
            "en la raíz del proyecto y pega tu llave (ANTHROPIC_API_KEY)."
        )
    try:
        from anthropic import Anthropic
    except ImportError as exc:  # pragma: no cover
        raise AISummaryError(
            "Falta instalar la librería 'anthropic' (revisa requirements.txt)."
        ) from exc
    extra_headers = {}
    if config.ANTHROPIC_WORKSPACE_ID:
        extra_headers["anthropic-workspace-id"] = config.ANTHROPIC_WORKSPACE_ID
    return Anthropic(api_key=config.ANTHROPIC_API_KEY, default_headers=extra_headers or None)


def _format_events_for_prompt(events: list[HealthEvent]) -> str:
    """Agrupa los eventos por categoría FHIR y los ordena por fecha, en texto plano legible."""
    by_category: dict[str, list[HealthEvent]] = defaultdict(list)
    for e in events:
        by_category[e.resource_type.value].append(e)

    lines = []
    # Orden fijo de categorías, para que el resumen sea consistente entre corridas.
    category_order = [
        "Condition", "MedicationStatement", "Observation",
        "DiagnosticReport", "Encounter", "Immunization", "Coverage",
    ]
    for category in category_order:
        cat_events = by_category.get(category, [])
        if not cat_events:
            continue
        cat_events.sort(key=lambda e: e.event_date_sort or date.min)
        lines.append(f"\n## {RESOURCE_LABELS_ES.get(category, category)}")
        for e in cat_events:
            parts = [f"- {e.event_date_text}: {e.title}"]
            if e.value:
                parts.append(f"valor={e.value}")
            if e.reference_range:
                parts.append(f"rango_referencia={e.reference_range}")
            if e.detail:
                parts.append(f"detalle={e.detail}")
            if e.institution:
                parts.append(f"fuente={e.institution}")
            lines.append(" | ".join(parts))
    return "\n".join(lines)


def _parse_json_response(raw_text: str) -> dict:
    text = raw_text.strip()
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise AISummaryError("La IA no devolvió un JSON reconocible. Intenta de nuevo.")
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise AISummaryError(f"La respuesta de la IA no es JSON válido: {exc}") from exc


def generate_health_summary(patient, events: list[HealthEvent]) -> dict:
    """
    Genera el resumen interpretativo para un paciente y su lista de eventos.
    Devuelve un dict con las claves: resumen_general, hallazgos, sugerencias,
    temas_para_el_medico. Lanza AISummaryError si algo falla.
    """
    if not events:
        raise AISummaryError("Este paciente todavía no tiene eventos de salud cargados.")

    client = _client()

    patient_info = (
        f"Paciente: {patient.full_name}. "
        f"Sexo: {patient.sex or 'no especificado'}. "
        f"Año de nacimiento aprox.: {patient.birth_year_approx or 'no especificado'}."
    )
    events_text = _format_events_for_prompt(events)

    full_prompt = (
        f"{patient_info}\n\nHistorial completo ({len(events)} registros):\n{events_text}"
        f"\n\n{PROMPT_INSTRUCTIONS}"
    )

    try:
        response = client.messages.create(
            model=config.ANTHROPIC_MODEL,
            max_tokens=4096,
            temperature=0,
            messages=[{"role": "user", "content": full_prompt}],
        )
    except Exception as exc:  # anthropic.APIError y subclases
        raise AISummaryError(f"No se pudo contactar a la API de Claude: {exc}") from exc

    raw_text = "".join(block.text for block in response.content if getattr(block, "type", None) == "text")
    data = _parse_json_response(raw_text)

    return {
        "resumen_general": data.get("resumen_general") or "",
        "hallazgos": data.get("hallazgos") or [],
        "sugerencias": data.get("sugerencias") or [],
        "temas_para_el_medico": data.get("temas_para_el_medico") or [],
    }
