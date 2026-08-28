"""
Modelos de datos, inspirados en las categorías de recursos de HL7 FHIR
(https://www.hl7.org/fhir/) — el estándar internacional de interoperabilidad
en salud usado en este proyecto.

Diseño:
- `Patient` es su propia tabla (como el recurso FHIR Patient).
- El resto de categorías (Condition, MedicationStatement, Observation,
  DiagnosticReport, Encounter, Immunization, Coverage) comparten una sola
  tabla `HealthEvent` con una columna `resource_type` como discriminador.
  Esto refleja la estructura que ya usamos en la hoja de cálculo cronológica
  y facilita el análisis/correlación posterior (todo evento de salud tiene
  la misma forma: fecha, tipo, detalle, valor, rango, institución, fuente).

  Cuando el proyecto necesite exportar/importar en formato FHIR real
  (por ejemplo para integrarse con una institución médica), cada fila de
  `HealthEvent` se puede traducir 1:1 a su recurso FHIR correspondiente —
  ver docs/ARQUITECTURA.md.
"""
import enum
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class ResourceType(str, enum.Enum):
    CONDITION = "Condition"
    MEDICATION_STATEMENT = "MedicationStatement"
    OBSERVATION = "Observation"
    DIAGNOSTIC_REPORT = "DiagnosticReport"
    ENCOUNTER = "Encounter"
    IMMUNIZATION = "Immunization"
    COVERAGE = "Coverage"


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    full_name: Mapped[str] = mapped_column(String(200))
    document_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    sex: Mapped[str | None] = mapped_column(String(20), nullable=True)
    birth_year_approx: Mapped[int | None] = mapped_column(Integer, nullable=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    insurer: Mapped[str | None] = mapped_column(String(200), nullable=True)
    eps: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    events: Mapped[list["HealthEvent"]] = relationship(
        back_populates="patient", cascade="all, delete-orphan"
    )


class HealthEvent(Base):
    """Un evento de salud/deporte, en cualquiera de las categorías FHIR soportadas."""

    __tablename__ = "health_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"))

    resource_type: Mapped[ResourceType] = mapped_column(Enum(ResourceType), index=True)

    # Fecha tal como aparece en la fuente (puede ser aproximada o un rango:
    # "jun-2024", "24-26/08/2026"), más una fecha normalizada para ordenar
    # y graficar cuando se puede determinar con precisión.
    event_date_text: Mapped[str] = mapped_column(String(40))
    event_date_sort: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)

    title: Mapped[str] = mapped_column(String(300))
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    value: Mapped[str | None] = mapped_column(String(300), nullable=True)
    reference_range: Mapped[str | None] = mapped_column(String(200), nullable=True)
    institution: Mapped[str | None] = mapped_column(String(300), nullable=True)
    source: Mapped[str | None] = mapped_column(String(300), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    patient: Mapped["Patient"] = relationship(back_populates="events")
