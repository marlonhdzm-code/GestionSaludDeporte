"""
Carga datos de PRUEBA para un paciente ficticio (Greg Welch, triatleta
aficionado con hipotiroidismo tratado) con 5 años de historial: 10 paneles
de laboratorio (dos por año, 12 marcadores cada uno) y 60 resúmenes
mensuales estilo reloj Garmin (VO2max, FC en reposo, HRV, horas de
entrenamiento, sueño, peso).

Objetivo: tener datos realistas para seguir desarrollando y probando la app
(tendencias, resumen con IA, etc.) sin usar los datos reales de Marlon. Este
paciente queda marcado como dato de prueba (document_id "TEST-GW-0001") y
aparece en el selector de paciente de la barra superior junto al paciente
real, una vez que haya más de un paciente cargado.

Uso:
    cd backend
    python -m app.seed_greg

Es seguro correrlo varias veces: si ya existe un paciente "Greg Welch", no
duplica nada.
"""
from . import crud, schemas
from .database import Base, SessionLocal, engine
from .greg_data import EVENTS, PATIENT
from .models import ResourceType


def run():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        existing = [p for p in crud.list_patients(db) if p.full_name == PATIENT["full_name"]]
        if existing:
            print(f"Ya existe el paciente de prueba '{PATIENT['full_name']}' "
                  f"(id={existing[0].id}); no se vuelve a cargar.")
            return

        patient = crud.create_patient(db, schemas.PatientCreate(**PATIENT))
        print(f"Paciente de prueba creado: {patient.full_name} (id={patient.id})")

        for date_text, rtype_name, title, detail, value, ref_range, institution, source, exact_date in EVENTS:
            event = schemas.HealthEventCreate(
                patient_id=patient.id,
                resource_type=ResourceType[rtype_name],
                event_date_text=date_text,
                event_date_sort=exact_date,
                title=title,
                detail=detail,
                value=value,
                reference_range=ref_range,
                institution=institution,
                source=source,
            )
            crud.create_event(db, event)

        print(f"{len(EVENTS)} eventos de prueba cargados para {patient.full_name}.")
        print("Corre 'uvicorn app.main:app --reload', abre http://127.0.0.1:8000 "
              "y usa el selector de paciente en la barra superior para verlo.")
    finally:
        db.close()


if __name__ == "__main__":
    run()
