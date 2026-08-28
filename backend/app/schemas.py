"""Esquemas Pydantic: definen la forma de los datos que entran y salen de la API."""
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from .models import ResourceType


class PatientBase(BaseModel):
    full_name: str
    document_id: str | None = None
    sex: str | None = None
    birth_year_approx: int | None = None
    city: str | None = None
    email: str | None = None
    insurer: str | None = None
    eps: str | None = None


class PatientCreate(PatientBase):
    pass


class PatientRead(PatientBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime


class HealthEventBase(BaseModel):
    resource_type: ResourceType
    event_date_text: str
    event_date_sort: date | None = None
    title: str
    detail: str | None = None
    value: str | None = None
    reference_range: str | None = None
    institution: str | None = None
    source: str | None = None


class HealthEventCreate(HealthEventBase):
    patient_id: int


class HealthEventUpdate(BaseModel):
    resource_type: ResourceType | None = None
    event_date_text: str | None = None
    event_date_sort: date | None = None
    title: str | None = None
    detail: str | None = None
    value: str | None = None
    reference_range: str | None = None
    institution: str | None = None
    source: str | None = None


class HealthEventRead(HealthEventBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    patient_id: int
    created_at: datetime
