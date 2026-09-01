"""
Datos de PRUEBA para un paciente ficticio: Greg Welch, triatleta aficionado
de 40 años con hipotiroidismo tratado. Sirven para seguir desarrollando y
probando la app (tendencias, resumen con IA, etc.) con un historial de 5
años, sin tocar los datos reales de Marlon.

Este módulo NO importa SQLAlchemy a propósito: así lo puede usar tanto
`app/seed_greg.py` (vía SQLAlchemy/crud, para correr con `python -m
app.seed_greg`) como un script simple que escriba directo a SQLite.

Los valores son sintéticos pero fisiológicamente razonables para un
triatleta aficionado con hipotiroidismo controlado, e incluyen 6 anomalías
"escondidas" (sin ningún Condition/diagnóstico que las etiquete) para poner
a prueba la Fase 3 (resumen con IA): la idea es ver si la IA las detecta
sola a partir de los números, igual que lo haría un profesional revisando
el historial. Ver la lista completa en docs/ANOMALIAS_PRUEBA_GREG.md.

Resumen de las 6 anomalías (para referencia — NO aparecen como texto en los
datos que ve la IA, solo como patrones numéricos):
1. Anemia ferropénica del deportista — caída de ferritina y hemoglobina en
   jul-2024, con recuperación parcial en los paneles siguientes.
2. Hipertensión arterial en ascenso — presión arterial sistólica que cruza
   el umbral de hipertensión (≥130) a partir de 2023.
3. Deficiencia estacional de vitamina D — valores bajos cada enero
   (invierno / menos sol), normales cada julio.
4. Síndrome de sobreentrenamiento — HRV en caída y frecuencia cardíaca en
   reposo en alza durante abr-jun 2023, con la carga de entrenamiento igual
   de alta (el patrón clásico de fatiga no compensada).
5. Tendinopatía rotuliana ("rodilla del corredor") — caída brusca de horas
   de entrenamiento en sep-oct 2022, con VO2max cayendo un poco y el peso
   subiendo apenas (siguió con algo de actividad cruzada).
6. Fascitis plantar — caída de horas de entrenamiento en feb-mar 2025, con
   una subida de peso algo mayor que en el caso anterior (menos actividad
   cruzada posible) y sin el patrón sistémico del sobreentrenamiento.
"""
import math
from datetime import date

PATIENT = dict(
    full_name="Greg Welch",
    document_id="TEST-GW-0001",
    sex="Masculino",
    birth_year_approx=1986,
    city="Boulder, Colorado, EE. UU. (paciente de prueba)",
    email="greg.welch.test@example.com",
    insurer="N/A — paciente de prueba",
    eps="N/A — paciente de prueba",
)

# --------------------------------------------------------------------------
# Laboratorio: 10 reportes (2 por año, 2021-2025), 14 marcadores cada uno.
# --------------------------------------------------------------------------
LAB_DATES = [date(y, m, 15) for y in range(2021, 2026) for m in (1, 7)]

LAB_SERIES = {
    "TSH (hormona tiroidea estimulante)": {
        "values": [8.9, 4.2, 2.1, 2.8, 3.4, 1.6, 2.3, 1.9, 2.6, 2.0],
        "unit": "mUI/L", "range": "0.35 – 4.94",
    },
    "T4 libre": {
        "values": [0.68, 0.95, 1.15, 1.22, 1.05, 1.28, 1.18, 1.32, 1.20, 1.30],
        "unit": "ng/dL", "range": "0.8 – 1.8",
    },
    "Colesterol total": {
        "values": [210, 195, 178, 170, 175, 165, 172, 160, 168, 158],
        "unit": "mg/dL", "range": "0 – 200 (óptimo)",
    },
    "Colesterol LDL": {
        "values": [130, 120, 105, 98, 100, 92, 96, 88, 92, 85],
        "unit": "mg/dL", "range": "< 100 (óptimo)",
    },
    "Colesterol HDL": {
        "values": [48, 52, 56, 58, 57, 60, 59, 62, 61, 64],
        "unit": "mg/dL", "range": "> 40 (deseable en hombres)",
    },
    "Triglicéridos": {
        "values": [140, 110, 95, 85, 90, 80, 88, 75, 82, 72],
        "unit": "mg/dL", "range": "< 150",
    },
    # --- anomalía 1: anemia ferropénica del deportista (jul-2024, índice 7) ---
    # con recuperación parcial en ene-2025 (índice 8) y completa en jul-2025 (índice 9).
    "Hemoglobina": {
        "values": [13.8, 14.2, 14.5, 13.9, 14.6, 14.1, 14.8, 12.6, 14.2, 14.6],
        "unit": "g/dL", "range": "13.5 – 17",
    },
    "Hematocrito": {
        "values": [41.5, 42.8, 43.5, 41.8, 44.0, 42.3, 44.5, 38.9, 42.5, 43.8],
        "unit": "%", "range": "40 – 54",
    },
    "Ferritina": {
        "values": [28, 35, 42, 30, 48, 33, 55, 14, 32, 45],
        "unit": "ng/mL",
        "range": "30 – 400 (frecuentemente baja en deportistas de resistencia)",
    },
    "Glucosa en ayunas": {
        "values": [90, 88, 86, 85, 87, 84, 86, 83, 85, 84],
        "unit": "mg/dL", "range": "60 – 100",
    },
    "Creatinina": {
        "values": [1.10, 1.15, 1.12, 1.18, 1.14, 1.20, 1.15, 1.22, 1.16, 1.19],
        "unit": "mg/dL",
        "range": "0.7 – 1.3 (frecuentemente en el límite alto por masa muscular)",
    },
    "CK (creatina quinasa)": {
        "values": [210, 340, 195, 410, 220, 380, 205, 395, 215, 405],
        "unit": "U/L",
        "range": "30 – 200 (frecuentemente elevada en deportistas de resistencia, más tras carreras)",
    },
    # --- anomalía 2: hipertensión arterial en ascenso desde 2023 (valor = sistólica) ---
    "Presión arterial": {
        "values_display": [
            "118/76 mmHg", "116/74 mmHg", "122/78 mmHg", "124/80 mmHg",
            "131/84 mmHg", "129/82 mmHg", "136/88 mmHg", "134/87 mmHg",
            "140/90 mmHg", "142/91 mmHg",
        ],
        "range": "< 130 (sistólica; ≥130/80 se considera elevada)",
    },
    # --- anomalía 3: deficiencia estacional de vitamina D (enero bajo, julio normal) ---
    "Vitamina D (25-OH)": {
        "values": [22, 38, 19, 41, 24, 45, 26, 43, 28, 44],
        "unit": "ng/mL", "range": "30 – 100 (insuficiencia < 30, deficiencia < 20)",
    },
}

INSTITUTION_LAB = "Laboratorio Clínico (dato de prueba)"


def _lab_events():
    events = []
    for title, spec in LAB_SERIES.items():
        if "values_display" in spec:
            pairs = zip(LAB_DATES, spec["values_display"])
            values_for_source = spec["values_display"]
        else:
            pairs = zip(LAB_DATES, [f"{v} {spec['unit']}" for v in spec["values"]])
            values_for_source = spec["values"]
        for d, value_text in pairs:
            events.append((
                d.strftime("%d/%m/%Y"), "OBSERVATION", title, None,
                value_text, spec["range"], INSTITUTION_LAB,
                f"Panel de laboratorio de prueba, {d.strftime('%m/%Y')}", d,
            ))
    return events


# --------------------------------------------------------------------------
# Condición y medicación: hipotiroidismo (la única condición diagnosticada
# explícitamente en los datos de prueba — las 6 anomalías de arriba/abajo
# quedan deliberadamente SIN diagnóstico, para poner a prueba la Fase 3).
# --------------------------------------------------------------------------
CONDITION_MED_EVENTS = [
    ("15/01/2021", "CONDITION", "Hipotiroidismo",
     "Diagnosticado por TSH elevada (8.9 mUI/L) y fatiga que afectaba el entrenamiento; inicia tratamiento",
     "TSH 8.9 mUI/L al diagnóstico", None, "Endocrinología (dato de prueba)",
     "Dato de prueba", date(2021, 1, 15)),
    ("15/01/2021", "MEDICATION_STATEMENT", "Levotiroxina",
     "Tratamiento de hipotiroidismo", "75 mcg, 1 vez al día en ayunas", None,
     "Endocrinología (dato de prueba)", "Dato de prueba", date(2021, 1, 15)),
    ("15/01/2023", "MEDICATION_STATEMENT", "Levotiroxina — ajuste de dosis",
     "Ajuste por TSH 3.4 mUI/L (límite superior del rango controlado)",
     "88 mcg, 1 vez al día en ayunas", None,
     "Endocrinología (dato de prueba)", "Dato de prueba", date(2023, 1, 15)),
]

ENCOUNTER_EVENTS = [
    (d.strftime("%d/%m/%Y"), "ENCOUNTER", "Consulta de endocrinología (control anual)",
     "Control de hipotiroidismo y ajuste de dosis si aplica", None, None,
     "Endocrinología (dato de prueba)", "Dato de prueba", d)
    for d in [date(y, 1, 15) for y in range(2021, 2026)]
]

# --------------------------------------------------------------------------
# Datos estilo Garmin: resumen mensual, 60 meses (ene-2021 a dic-2025)
# --------------------------------------------------------------------------


def _month_range(start_year, start_month, n_months):
    y, m = start_year, start_month
    out = []
    for _ in range(n_months):
        out.append(date(y, m, 1))
        m += 1
        if m > 12:
            m = 1
            y += 1
    return out


MONTHS = _month_range(2021, 1, 60)
GARMIN_INSTITUTION = "Reloj Garmin (dato de prueba, resumen mensual)"


def _month_index(year: int, month: int) -> int:
    return (year - 2021) * 12 + (month - 1)


# --- anomalía 4: sobreentrenamiento, abr-jun 2023 (HRV cae, FC reposo sube,
#     sueño cae, pero las horas de entrenamiento se mantienen altas) ---
_OVERTRAINING_IDX = {
    _month_index(2023, 4): dict(hrv=50, fc_reposo=54, sueno=6.3, horas_entreno=10.4),
    _month_index(2023, 5): dict(hrv=45, fc_reposo=57, sueno=6.0, horas_entreno=11.0),
    _month_index(2023, 6): dict(hrv=43, fc_reposo=59, sueno=5.9, horas_entreno=10.7),
}

# --- anomalía 5: tendinopatía rotuliana, sep-oct 2022 (deja de correr,
#     algo de actividad cruzada: peso casi estable, VO2max baja un poco) ---
_RUNNERS_KNEE_IDX = {
    _month_index(2022, 9): dict(horas_entreno=4.2, vo2max_delta=-1.0, peso_delta=0.3),
    _month_index(2022, 10): dict(horas_entreno=3.8, vo2max_delta=-1.4, peso_delta=0.4),
}

# --- anomalía 6: fascitis plantar, feb-mar 2025 (menos actividad cruzada
#     que en la lesión de rodilla: el peso sube más) ---
_PLANTAR_FASCIITIS_IDX = {
    _month_index(2025, 2): dict(horas_entreno=5.0, vo2max_delta=-1.2, peso_delta=0.6),
    _month_index(2025, 3): dict(horas_entreno=4.5, vo2max_delta=-1.6, peso_delta=0.8),
}


def _garmin_events():
    events = []
    for i, d in enumerate(MONTHS):
        year_progress = i / 59  # 0 a 1 a lo largo de los 5 años (mejora por entrenamiento)
        season = math.sin(2 * math.pi * (d.month - 3) / 12)  # pico ~jun-jul (temporada de carreras)
        jitter = ((i * 37) % 11 - 5) / 10  # variación pequeña, determinística (no aleatoria real)

        vo2max = round(46 + 7 * year_progress + 1.5 * season + jitter, 1)
        fc_reposo = round(54 - 8 * year_progress - 1.5 * season + jitter)
        hrv = round(58 + 8 * year_progress + 4 * season + jitter)
        horas_entreno = round(6.5 + 2.5 * year_progress + 2.2 * season + jitter * 0.5, 1)
        sueno = round(6.6 + 0.5 * year_progress + 0.3 * season + jitter * 0.2, 1)
        peso = round(89 - 5 * year_progress - 0.6 * season + jitter * 0.3, 1)

        if i in _OVERTRAINING_IDX:
            o = _OVERTRAINING_IDX[i]
            hrv, fc_reposo, sueno, horas_entreno = o["hrv"], o["fc_reposo"], o["sueno"], o["horas_entreno"]
        if i in _RUNNERS_KNEE_IDX:
            o = _RUNNERS_KNEE_IDX[i]
            horas_entreno = o["horas_entreno"]
            vo2max = round(vo2max + o["vo2max_delta"], 1)
            peso = round(peso + o["peso_delta"], 1)
        if i in _PLANTAR_FASCIITIS_IDX:
            o = _PLANTAR_FASCIITIS_IDX[i]
            horas_entreno = o["horas_entreno"]
            vo2max = round(vo2max + o["vo2max_delta"], 1)
            peso = round(peso + o["peso_delta"], 1)

        metrics = [
            ("VO2max estimado (Garmin)", vo2max, "ml/kg/min",
             "45 – 60 (bueno–excelente, hombre 35-45 años)"),
            ("Frecuencia cardíaca en reposo (Garmin)", fc_reposo, "lpm",
             "40 – 60 (rango deportista entrenado)"),
            ("Variabilidad de frecuencia cardíaca — HRV (Garmin)", hrv, "ms",
             "Mayor valor = mejor recuperación (referencia personal, no clínica)"),
            ("Horas de entrenamiento semanal, promedio del mes (Garmin)", horas_entreno,
             "horas/semana", "6 – 11 (típico triatleta aficionado)"),
            ("Sueño promedio (Garmin)", sueno, "horas/noche", "7 – 9 (recomendado en adultos)"),
            ("Peso corporal (Garmin)", peso, "kg", None),
        ]
        for title, value, unit, ref in metrics:
            events.append((
                d.strftime("%m/%Y"), "OBSERVATION", title, None,
                f"{value} {unit}", ref, GARMIN_INSTITUTION,
                f"Resumen mensual Garmin, {d.strftime('%m/%Y')} (dato de prueba)", d,
            ))
    return events


# (fecha_texto, resource_type [nombre del enum], título, detalle, valor,
#  rango de referencia, institución, fuente, fecha_exacta)
EVENTS = _lab_events() + CONDITION_MED_EVENTS + ENCOUNTER_EVENTS + _garmin_events()
