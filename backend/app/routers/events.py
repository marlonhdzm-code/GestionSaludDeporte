from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..database import get_db

router = APIRouter(prefix="/api/events", tags=["events"])


@router.get("", response_model=list[schemas.HealthEventRead])
def list_events(
    patient_id: int | None = None,
    resource_type: models.ResourceType | None = None,
    db: Session = Depends(get_db),
):
    """Lista eventos de salud, opcionalmente filtrados por paciente y/o categoría FHIR."""
    return crud.list_events(db, patient_id=patient_id, resource_type=resource_type)


@router.post("", response_model=schemas.HealthEventRead, status_code=201)
def create_event(event: schemas.HealthEventCreate, db: Session = Depends(get_db)):
    if crud.get_patient(db, event.patient_id) is None:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    return crud.create_event(db, event)


@router.get("/{event_id}", response_model=schemas.HealthEventRead)
def get_event(event_id: int, db: Session = Depends(get_db)):
    event = crud.get_event(db, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Evento no encontrado")
    return event


@router.put("/{event_id}", response_model=schemas.HealthEventRead)
def update_event(event_id: int, changes: schemas.HealthEventUpdate, db: Session = Depends(get_db)):
    event = crud.update_event(db, event_id, changes)
    if event is None:
        raise HTTPException(status_code=404, detail="Evento no encontrado")
    return event


@router.delete("/{event_id}", status_code=204)
def delete_event(event_id: int, db: Session = Depends(get_db)):
    if not crud.delete_event(db, event_id):
        raise HTTPException(status_code=404, detail="Evento no encontrado")
