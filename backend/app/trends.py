"""
Interpretación de los campos de texto libre `value` y `reference_range` como
números, para poder graficarlos en /tendencias.

Es intencionalmente "best effort": estos campos se guardan como texto libre
(tal como aparecen en el documento original: "190 mg/dL", "0 – 200 (óptimo)",
"< 3.1 (51–60 años)"...), así que no siempre se pueden interpretar con
certeza. Cuando no se puede, la función devuelve None y ese punto
simplemente no aparece en la gráfica — nunca se inventa un valor.

Limitación conocida: para números con separador de miles en formato
latinoamericano (ej. "6.240" leucocitos = seis mil doscientos cuarenta), el
punto se interpreta igual que un separador decimal ("6.240" -> 6.24). Esto
es correcto para la inmensa mayoría de valores clínicos de esta app
(colesterol, glucosa, creatinina, TSH...) pero subestima recuentos grandes
(leucocitos, plaquetas). Ver docs/ARQUITECTURA.md.
"""
import re

_NUMBER_RE = re.compile(r"-?\d+(?:[.,]\d+)?")
_RANGE_RE = re.compile(
    r"(-?\d+(?:[.,]\d+)?)\s*(?:[-–—]|a)\s*(-?\d+(?:[.,]\d+)?)"
)
_PAREN_RE = re.compile(r"\([^)]*\)")
_UPPER_BOUND_ONLY_RE = re.compile(r"[<≤]\s*(-?\d+(?:[.,]\d+)?)")


def parse_numeric_value(value: str | None) -> float | None:
    """Extrae el primer número que aparece en un texto como '190 mg/dL'."""
    if not value:
        return None
    match = _NUMBER_RE.search(value.replace(",", "."))
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def parse_reference_range(range_text: str | None) -> tuple[float, float] | None:
    """
    Extrae (mínimo, máximo) de un texto como '0 – 200 (óptimo)'.

    Antes de buscar el patrón "número - número" se quita cualquier paréntesis
    — textos como '< 3.1 (51–60 años)' traen un rango de edad entre
    paréntesis que NO es el rango de referencia del analito, y sin este paso
    se confundiría uno con otro. Un texto tipo '< 3.1' (sin límite inferior
    explícito) se interpreta como (0, 3.1), asumiendo que el valor clínico
    no puede ser negativo.
    """
    if not range_text:
        return None
    text = _PAREN_RE.sub(" ", range_text.replace(",", "."))

    match = _RANGE_RE.search(text)
    if match:
        try:
            lo, hi = float(match.group(1)), float(match.group(2))
        except ValueError:
            return None
        return (lo, hi) if lo <= hi else (hi, lo)

    match = _UPPER_BOUND_ONLY_RE.search(text)
    if match:
        try:
            return (0.0, float(match.group(1)))
        except ValueError:
            return None

    return None
