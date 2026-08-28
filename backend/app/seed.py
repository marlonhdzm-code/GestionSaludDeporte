"""
Carga los datos iniciales de salud (extraídos y verificados manualmente del
correo electrónico) en la base de datos.

Uso:
    cd backend
    python -m app.seed

Es seguro correrlo varias veces mientras la base esté vacía; si ya hay un
paciente cargado, no duplica nada.
"""
from datetime import date, datetime

from . import crud, schemas
from .database import Base, SessionLocal, engine
from .models import ResourceType

PATIENT = schemas.PatientCreate(
    full_name="Marlon Alberto Hernández Arboleda",
    document_id="71.694.040",
    sex="Masculino",
    birth_year_approx=1967,
    city="Medellín, Colombia",
    email="hdzm@hotmail.com",
    insurer="Seguros de Vida Suramericana S.A. — SURA, póliza clásica",
    eps="EPS SURA",
)

R = ResourceType


def _d(day: int, month: int, year: int) -> date:
    return date(year, month, day)


# (fecha_texto, categoría, título, detalle, valor, rango, institución, fuente, fecha_exacta_opcional)
EVENTS = [
    ("25/07/2019", R.DIAGNOSTIC_REPORT, "Nasofibrolaringoscopia",
     "Estudio otorrinolaringológico inicial", None, None,
     "ORLANT — Dra. Amalia Botero Cock", "Correo con informe adjunto, jul-2019", _d(25, 7, 2019)),
    ("25/07/2019", R.CONDITION, "Desviación septal e hipertrofia de cornetes inferiores (bilateral)",
     "Hallazgo estructural nasal", None, None,
     "ORLANT — Dra. Amalia Botero Cock", "Informe nasofibrolaringoscopia 25/07/2019", _d(25, 7, 2019)),
    ("25/07/2019", R.CONDITION, "Laringitis posterior y sospecha de rinosinusitis alérgica derecha",
     "Hallazgo activo en el momento del estudio", None, None,
     "ORLANT — Dra. Amalia Botero Cock", "Informe nasofibrolaringoscopia 25/07/2019", _d(25, 7, 2019)),

    ("11/06/2020", R.DIAGNOSTIC_REPORT, "Ecografía de vías urinarias",
     "Riñones, vejiga y próstata sin hallazgos patológicos", "Próstata 42×22×34 mm, 17 cc", "Normal",
     "SaludSura", "Correo con informe adjunto, jun-2020", _d(11, 6, 2020)),
    ("16/06/2020", R.OBSERVATION, "Parcial de orina — color", None, "Ámbar", "Ámbar a Amarillo",
     "SaludSura — Dr. Andrés Roldán Aragón", "Informe laboratorio 16/06/2020", _d(16, 6, 2020)),
    ("16/06/2020", R.OBSERVATION, "Parcial de orina — aspecto", None, "Claro", "Transparente a Límpido",
     "SaludSura — Dr. Andrés Roldán Aragón", "Informe laboratorio 16/06/2020", _d(16, 6, 2020)),
    ("16/06/2020", R.OBSERVATION, "Densidad urinaria", None, "1.023", "1.005 – 1.030",
     "SaludSura — Dr. Andrés Roldán Aragón", "Informe laboratorio 16/06/2020", _d(16, 6, 2020)),
    ("16/06/2020", R.OBSERVATION, "pH urinario", None, "7.0", "5.0 – 6.5 (fuera de rango)",
     "SaludSura — Dr. Andrés Roldán Aragón", "Informe laboratorio 16/06/2020", _d(16, 6, 2020)),
    ("16/06/2020", R.OBSERVATION, "Proteínas, glucosa, cetonas, bilirrubina, sangre, nitritos (orina)",
     None, "Negativo", "Negativo",
     "SaludSura — Dr. Andrés Roldán Aragón", "Informe laboratorio 16/06/2020", _d(16, 6, 2020)),
    ("16/06/2020", R.OBSERVATION, "Leucocitos (sedimento urinario)", None, "2", "0 – 8 por AP",
     "SaludSura — Dr. Andrés Roldán Aragón", "Informe laboratorio 16/06/2020", _d(16, 6, 2020)),
    ("16/06/2020", R.OBSERVATION, "Eritrocitos (sedimento urinario)", None, "2", "0 – 3 por AP",
     "SaludSura — Dr. Andrés Roldán Aragón", "Informe laboratorio 16/06/2020", _d(16, 6, 2020)),
    ("16/06/2020", R.OBSERVATION, "Antígeno prostático específico (PSA)", None, "0.41 ng/mL", "< 3.1 (51–60 años)",
     "SaludSura — Dr. Andrés Roldán Aragón", "Informe laboratorio 16/06/2020", _d(16, 6, 2020)),

    ("08/10/2020", R.DIAGNOSTIC_REPORT, "Holter + Ecocardiograma (orden médica)",
     "Bradicardia sinusal fisiológica del deportista", "38 lpm en ECG de reposo", None,
     "Dr. Hugo Giraldo Dávila — SaludSura Industriales", "Correo con orden/informe, oct-2020", _d(8, 10, 2020)),
    ("08/10/2020", R.CONDITION, "Bradicardia sinusal fisiológica del deportista",
     "Contexto: COVID-19 asintomático a nivel cardíaco", "38 lpm", None,
     "Dr. Hugo Giraldo Dávila", "Correo oct-2020", _d(8, 10, 2020)),

    ("15/11/2023", R.DIAGNOSTIC_REPORT, "Nasofibrolaringoscopia (control)",
     "Hallazgos nasales estables (cresta/espolón septal, cornete inferior hipertrófico), sin deterioro",
     None, None, "ORLANT", "Correo con informe adjunto, nov-2023", _d(15, 11, 2023)),

    ("11/03/2024", R.DIAGNOSTIC_REPORT, "Ecocardiograma transtorácico",
     "Resultado disponible solo en portal web del paciente; no se pudo extraer el valor del correo",
     "No disponible en correo", None, "Clínica Las Américas Aúna", "Correo de notificación, mar-2024", _d(11, 3, 2024)),

    ("29/04/2024", R.ENCOUNTER, "Consulta de cardiología", "Realizada", None, None,
     "Dr. Álvaro Quintero — CardioVID", "Correo confirmación de cita, abr-2024", _d(29, 4, 2024)),
    ("29/04/2024", R.MEDICATION_STATEMENT, "Valsartán", "Antihipertensivo / cardiológico",
     "80 mg (se toma media tableta = 40 mg), 1 vez al día", None,
     "Dr. Álvaro Quintero — CardioVID", "Correo del paciente a CardioVID, abr-jun 2024", _d(29, 4, 2024)),
    ("29/04/2024", R.MEDICATION_STATEMENT, "Empagliflozina", "Protección renal / cardíaca (inhibidor SGLT2)",
     "10 mg, 1 vez al día", None,
     "Dr. Álvaro Quintero — CardioVID", "Correo del paciente a CardioVID, abr-jun 2024", _d(29, 4, 2024)),
    ("02/05/2024", R.MEDICATION_STATEMENT, "Valsartán — ajuste de dosis",
     "Ajuste por desabastecimiento de la presentación de 40 mg", "40 mg, 1 vez al día", None,
     "Dr. Álvaro Quintero — CardioVID", "Correo del paciente, 02/05/2024", _d(2, 5, 2024)),

    ("13/06/2024", R.DIAGNOSTIC_REPORT, "Ecocardiograma",
     'Descrito por el paciente como "con resultados positivos" (con hallazgos relevantes); motivó adelantar la resonancia cardíaca',
     "No especificado en el correo", None, "No especificado en el correo", "Correo del paciente, jun-2024", _d(13, 6, 2024)),

    ("24/06/2024", R.OBSERVATION, "Colesterol LDL", None, "190 mg/dL", None,
     "CardioVID (reportado por el paciente)", "Correo del paciente a CardioVID, 24/06/2024", _d(24, 6, 2024)),
    ("24/06/2024", R.OBSERVATION, "Colesterol total", None, "265 mg/dL", None,
     "CardioVID (reportado por el paciente)", "Correo del paciente a CardioVID, 24/06/2024", _d(24, 6, 2024)),
    ("24/06/2024", R.OBSERVATION, "Colesterol VLDL", None, "33 mg/dL", None,
     "CardioVID (reportado por el paciente)", "Correo del paciente a CardioVID, 24/06/2024", _d(24, 6, 2024)),
    ("24/06/2024", R.OBSERVATION, "Colesterol HDL", None, "53 mg/dL", None,
     "CardioVID (reportado por el paciente)", "Correo del paciente a CardioVID, 24/06/2024", _d(24, 6, 2024)),
    ("24/06/2024", R.OBSERVATION, "Triglicéridos", None, "163 mg/dL", None,
     "CardioVID (reportado por el paciente)", "Correo del paciente a CardioVID, 24/06/2024", _d(24, 6, 2024)),
    ("24/06/2024", R.OBSERVATION, "Creatinina (suero)", None, "1.2 mg/dL", None,
     "CardioVID (reportado por el paciente)", "Correo del paciente a CardioVID, 24/06/2024", _d(24, 6, 2024)),
    ("24/06/2024", R.OBSERVATION, "Glucosa", None, "99 mg/dL", None,
     "CardioVID (reportado por el paciente)", "Correo del paciente a CardioVID, 24/06/2024", _d(24, 6, 2024)),
    ("24/06/2024", R.OBSERVATION, "Hemoglobina glicada (HbA1c)", None, "5.4 %", None,
     "CardioVID (reportado por el paciente)", "Correo del paciente a CardioVID, 24/06/2024", _d(24, 6, 2024)),
    ("24/06/2024", R.OBSERVATION, "Glucosa promedio últimos 3 meses (estimada)", None, "108 mg/dL", None,
     "CardioVID (reportado por el paciente)", "Correo del paciente a CardioVID, 24/06/2024", _d(24, 6, 2024)),
    ("24/06/2024", R.OBSERVATION, "Microalbuminuria", None, "2.0", None,
     "CardioVID (reportado por el paciente)", "Correo del paciente a CardioVID, 24/06/2024", _d(24, 6, 2024)),
    ("24/06/2024", R.OBSERVATION, "Albúmina en orina", None, "3.17", None,
     "CardioVID (reportado por el paciente)", "Correo del paciente a CardioVID, 24/06/2024", _d(24, 6, 2024)),
    ("24/06/2024", R.OBSERVATION, "Creatinina en orina", None, "158", None,
     "CardioVID (reportado por el paciente)", "Correo del paciente a CardioVID, 24/06/2024", _d(24, 6, 2024)),
    ("24/06/2024", R.OBSERVATION, "Nitrógeno ureico", None, "22.4", None,
     "CardioVID (reportado por el paciente)", "Correo del paciente a CardioVID, 24/06/2024", _d(24, 6, 2024)),
    ("jun-2024", R.MEDICATION_STATEMENT, "Rosuvastatina",
     "Colesterol elevado (LDL 190, colesterol total 265 el 24/06/2024)",
     "20 mg, 1 vez al día en la noche", None,
     "Dr. Álvaro Quintero — CardioVID", "Correo del paciente, jun-2024", None),
    ("24/06/2024", R.CONDITION, "Dislipidemia (colesterol elevado)",
     "LDL 190 mg/dL y colesterol total 265 mg/dL, ambos por encima del rango de referencia; "
     "en tratamiento con estatina desde jun-2024",
     "LDL 190, CT 265 mg/dL", "Óptimo: LDL <100 según contexto",
     "CardioVID", "Correo del paciente, 24/06/2024", _d(24, 6, 2024)),

    ("26/06/2024", R.ENCOUNTER, "Control con medicina interna", "Realizada", None, None,
     "No especificado", "Correo confirmación de cita, jun-2024", _d(26, 6, 2024)),

    ("05/07/2024", R.ENCOUNTER, "Consulta de cardiología (seguimiento)",
     "Programada; se gestionó posible reprogramación", None, None,
     "Dr. Álvaro Quintero — CardioVID", "Correo confirmación de cita, jul-2024", _d(5, 7, 2024)),

    ("29/08/2024", R.DIAGNOSTIC_REPORT, "Resonancia magnética de corazón (con caracterización tisular)",
     'Solicitada tras ecocardiograma (13/06/2024) "con resultados positivos"; '
     "resultado no localizado en el correo",
     "No localizado en el correo", None,
     "Gestionada en Hospital Pablo Tobón Uribe y Clínica Las Américas",
     "Correo de gestión de cita, abr-ago 2024", _d(29, 8, 2024)),

    ("feb-2025", R.COVERAGE, "Trámite administrativo EPS",
     "Solicitud registrada ante EPS SURA (carácter administrativo, no clínico)",
     None, None, "EPS SURA", "Correo de trámite, feb-2025", None),
    ("sep-2025", R.COVERAGE, "Trámite administrativo EPS",
     "Solicitud registrada ante EPS SURA (carácter administrativo, no clínico)",
     None, None, "EPS SURA", "Correo de trámite, sep-2025", None),
    ("12/12/2025", R.ENCOUNTER, "Ecocardiograma transtorácico (programado)",
     "Cita programada; recordatorio recibido 10/12/2025", None, None,
     "SaludSura Sao Paulo", "Correo recordatorio, dic-2025", _d(12, 12, 2025)),
    ("12/12/2025", R.DIAGNOSTIC_REPORT, "Ecocardiograma transtorácico (programado)",
     "Resultado no incluido en el correo revisado", "No disponible", None,
     "SaludSura Sao Paulo", "Correo recordatorio, dic-2025", _d(12, 12, 2025)),

    ("30/06/2026", R.IMMUNIZATION, "Vacunación (tipo no especificado)",
     "Cita programada; tipo de vacuna no especificado en el correo de confirmación", None, None,
     "SaludSura Sao Paulo", "Correo confirmación de cita, jun-2026", _d(30, 6, 2026)),

    ("19/08/2026", R.ENCOUNTER, "Medicina general — cancelación",
     "Cita del 20/08/2026 cancelada a solicitud del paciente", None, None,
     "Isabela Jiménez Moreno — SaludSura Sao Paulo", "Correo de cancelación, 19/08/2026", _d(19, 8, 2026)),
    ("20/08/2026", R.ENCOUNTER, "Medicina general", "CANCELADA (ver 19/08/2026)", None, None,
     "Isabela Jiménez Moreno — SaludSura Sao Paulo", "Correo confirmación de cita original", _d(20, 8, 2026)),

    ("24-26/08/2026", R.OBSERVATION, "Colesterol total", "Chequeo general SURA (el más reciente)",
     "137 mg/dL", "0 – 200 (óptimo)", "SURA", "Informe laboratorio 24-26/08/2026", _d(24, 8, 2026)),
    ("24-26/08/2026", R.OBSERVATION, "Colesterol HDL", "Chequeo general SURA (el más reciente)",
     "54 mg/dL", "Riesgo moderado 35–55 (H)", "SURA", "Informe laboratorio 24-26/08/2026", _d(24, 8, 2026)),
    ("24-26/08/2026", R.OBSERVATION, "Creatinina sérica", "Chequeo general SURA (el más reciente)",
     "1.05 mg/dL", "0.67 – 1.17", "SURA", "Informe laboratorio 24-26/08/2026", _d(24, 8, 2026)),
    ("24-26/08/2026", R.OBSERVATION, "Glucosa en ayunas", "Chequeo general SURA (el más reciente)",
     "96 mg/dL", "60 – 100", "SURA", "Informe laboratorio 24-26/08/2026", _d(24, 8, 2026)),
    ("24-26/08/2026", R.OBSERVATION, "TSH (hormona tiroidea estimulante)", "Chequeo general SURA (el más reciente)",
     "2.766 mUI/L", "0.35 – 4.94", "SURA", "Informe laboratorio 24-26/08/2026", _d(24, 8, 2026)),
    ("24-26/08/2026", R.OBSERVATION, "Parcial de orina (incluido sedimento)", "Chequeo general SURA (el más reciente)",
     "Normal (sin alteraciones)", None, "SURA", "Informe laboratorio 24-26/08/2026", _d(24, 8, 2026)),
    ("24-26/08/2026", R.OBSERVATION, "Hemograma — leucocitos totales", "Chequeo general SURA (el más reciente)",
     "6.240", "4.500 – 11.000 mm³", "SURA", "Informe laboratorio 24-26/08/2026", _d(24, 8, 2026)),
    ("24-26/08/2026", R.OBSERVATION, "Hemograma — hemoglobina", "Chequeo general SURA (el más reciente)",
     "14.9 g/dL", "13.5 – 17", "SURA", "Informe laboratorio 24-26/08/2026", _d(24, 8, 2026)),
    ("24-26/08/2026", R.OBSERVATION, "Hemograma — hematocrito", "Chequeo general SURA (el más reciente)",
     "44.9 %", "40 – 54", "SURA", "Informe laboratorio 24-26/08/2026", _d(24, 8, 2026)),
    ("24-26/08/2026", R.OBSERVATION, "Hemograma — plaquetas", "Chequeo general SURA (el más reciente)",
     "243.000", "150.000 – 450.000 mm³", "SURA", "Informe laboratorio 24-26/08/2026", _d(24, 8, 2026)),
    ("24-26/08/2026", R.OBSERVATION, "Hemograma — linfocitos (%)",
     "Chequeo general SURA (el más reciente); levemente alto",
     "45.6 %", "20 – 45", "SURA", "Informe laboratorio 24-26/08/2026", _d(24, 8, 2026)),
    ("24-26/08/2026", R.CONDITION, "Dislipidemia — seguimiento",
     "Colesterol total bajó a 137 mg/dL (rango óptimo) para ago-2026, en tratamiento con estatina",
     "CT 137 mg/dL", "0 – 200 (óptimo)", "SURA", "Informe laboratorio 24-26/08/2026", _d(24, 8, 2026)),
]


def run():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        existing = crud.list_patients(db)
        if existing:
            print(f"Ya hay {len(existing)} paciente(s) en la base de datos; no se vuelve a cargar. "
                  f"Borra el archivo salud_deporte.db si quieres empezar de cero.")
            return

        patient = crud.create_patient(db, PATIENT)
        print(f"Paciente creado: {patient.full_name} (id={patient.id})")

        for date_text, rtype, title, detail, value, ref_range, institution, source, exact_date in EVENTS:
            event = schemas.HealthEventCreate(
                patient_id=patient.id,
                resource_type=rtype,
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

        print(f"{len(EVENTS)} eventos de salud cargados correctamente.")
        print(f"Corre 'uvicorn app.main:app --reload' y abre http://127.0.0.1:8000 para verlos.")
    finally:
        db.close()


if __name__ == "__main__":
    run()
