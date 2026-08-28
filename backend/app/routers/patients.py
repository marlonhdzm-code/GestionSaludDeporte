from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..database import get_db

router = APIRouter(prefix="/api/patients", tags=["patients"])


@router.get("", response_model=list[schemas.PatientRead])
def list_patients(db: Session = Depends(get_db)):
    return crud.list_patients(db)


@router.post("", response_model=schemas.PatientRead, status_code=201)
def create_patient(patient: schemas.PatientCreate, db: Session = Depends(get_db)):
    return crud.create_patient(db, patient)


@router.get("/{patient_id}", response_model=schemas.PatientRead)
def get_patient(patient_id: int, db: Session = Depends(get_db)):
    patient = crud.get_patient(db, patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    return patient
