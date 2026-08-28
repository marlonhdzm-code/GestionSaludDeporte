"""Funciones de acceso a datos (Create/Read/Update/Delete), sin lógica de HTTP."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models, schemas


# --- Patient -----------------------------------------------------------------

def create_patient(db: Session, patient: schemas.PatientCreate) -> models.Patient:
    db_patient = models.Patient(**patient.model_dump())
    db.add(db_patient)
    db.commit()
    db.refresh(db_patient)
    return db_patient


def get_patient(db: Session, patient_id: int) -> models.Patient | None:
    return db.get(models.Patient, patient_id)


def list_patients(db: Session) -> list[models.Patient]:
    return list(db.scalars(select(models.Patient)))


# --- HealthEvent ---------------------------------------------------------------

def create_event(db: Session, event: schemas.HealthEventCreate) -> models.HealthEvent:
    db_event = models.HealthEvent(**event.model_dump())
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    return db_event


def get_event(db: Session, event_id: int) -> models.HealthEvent | None:
    return db.get(models.HealthEvent, event_id)


def list_events(
    db: Session,
    patient_id: int | None = None,
    resource_type: models.ResourceType | None = None,
) -> list[models.HealthEvent]:
    stmt = select(models.HealthEvent)
    if patient_id is not None:
        stmt = stmt.where(models.HealthEvent.patient_id == patient_id)
    if resource_type is not None:
        stmt = stmt.where(models.HealthEvent.resource_type == resource_type)
    stmt = stmt.order_by(
        models.HealthEvent.event_date_sort.is_(None),  # los que sí tienen fecha exacta primero
        models.HealthEvent.event_date_sort,
        models.HealthEvent.id,
    )
    return list(db.scalars(stmt))


def update_event(
    db: Session, event_id: int, changes: schemas.HealthEventUpdate
) -> models.HealthEvent | None:
    db_event = get_event(db, event_id)
    if db_event is None:
        return None
    for field, value in changes.model_dump(exclude_unset=True).items():
        setattr(db_event, field, value)
    db.commit()
    db.refresh(db_event)
    return db_event


def delete_event(db: Session, event_id: int) -> bool:
    db_event = get_event(db, event_id)
    if db_event is None:
        return False
    db.delete(db_event)
    db.commit()
    return True


def counts_by_category(db: Session, patient_id: int) -> dict[str, int]:
    events = list_events(db, patient_id=patient_id)
    counts = {rt.value: 0 for rt in models.ResourceType}
    for e in events:
        counts[e.resource_type.value] += 1
    return counts
