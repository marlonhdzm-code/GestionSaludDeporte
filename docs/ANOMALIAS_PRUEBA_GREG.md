# Clave de respuestas: anomalías de prueba en los datos de Greg Welch

> Este archivo es la clave de respuestas para evaluar objetivamente la Fase 3 (resumen con
> IA). **Ninguna de estas 6 condiciones aparece como texto, diagnóstico o `Condition` en los
> datos que ve la app** — solo existen como patrones numéricos en los paneles de laboratorio
> y en los resúmenes mensuales de Garmin del paciente de prueba "Greg Welch"
> (`backend/app/greg_data.py`, `document_id="TEST-GW-0001"`). La idea es correr `/resumen`
> sobre estos datos y comparar lo que la IA detecta contra esta lista — sin haberle dado la
> respuesta de antemano.

## 3 condiciones detectables en exámenes de laboratorio

**1. Anemia ferropénica del deportista**
- Ferritina cae a 14 ng/mL (rango 30–400) y Hemoglobina cae a 12.6 g/dL (rango 13.5–17, por
  debajo del límite) en el panel de **julio 2024**.
- Recuperación parcial en enero 2025 (Ferritina 32, Hemoglobina 14.2) y completa en julio
  2025 (Ferritina 45, Hemoglobina 14.6).
- Lo esperable: que la IA note la caída puntual y sugiera suplementación de hierro /
  evaluación de anemia del deportista, y que reconozca que ya se recuperó en los paneles
  siguientes.

**2. Hipertensión arterial en ascenso**
- Marcador "Presión arterial" (formato "sistólica/diastólica mmHg") en los 10 paneles, con
  tendencia clara al alza: 118/76 (ene-2021) → 142/91 (jul-2025), cruzando el umbral de
  hipertensión (≥130/80) desde **2023** en adelante.
- Nota técnica: el parser de tendencias (`app/trends.py`) solo grafica el primer número (la
  sistólica); la diastólica queda en el texto del valor (`raw_value`) pero no en el gráfico —
  si la Fase 3 usa el `value` crudo en vez de solo el punto graficado, debería poder leer
  ambas cifras.
- Lo esperable: que la IA note que, pese a ser un deportista de resistencia (que normalmente
  tiene presión baja), la tendencia ascendente cruza a hipertensión estadio 1 y amerite
  evaluación médica.

**3. Deficiencia estacional de vitamina D**
- Marcador "Vitamina D (25-OH)": valores bajos cada **enero** (22, 19, 24, 26, 28 ng/mL —
  insuficiencia/deficiencia, rango normal 30–100) y normales cada **julio** (38, 41, 45, 43,
  44 ng/mL).
- Lo esperable: que la IA note el patrón estacional (probablemente por menos exposición solar
  / más entrenamiento indoor en invierno) y sugiera suplementación en los meses fríos.

## 3 condiciones deportivas detectables en datos de Garmin

**4. Síndrome de sobreentrenamiento (abr–jun 2023)**
- HRV cae de ~62 a 43 ms, frecuencia cardíaca en reposo sube de ~50 a 59 lpm, sueño cae de
  ~6.8 a 5.9 h/noche — **mientras las horas de entrenamiento semanal siguen altas o suben**
  (7.6 → 11.0 h/semana). Es el patrón clásico de fatiga acumulada sin recuperación adecuada.
- Lo esperable: que la IA cruce estas 4 métricas (no solo una) y sugiera reducir carga /
  priorizar recuperación antes de una lesión o enfermedad mayor.

**5. Tendinopatía rotuliana / "rodilla del corredor" (sep–oct 2022)**
- Caída brusca de horas de entrenamiento (8.7 → 4.2 → 3.8 h/semana), con VO2max bajando
  apenas (49.5 → 46.5) y peso subiendo levemente (87.2 → 88.0 kg) — consistente con que dejó
  de correr pero mantuvo algo de actividad cruzada (nado/bici).
- Lo esperable: que la IA identifique la caída de carga como probable lesión (no enfermedad
  general, dado que el resto de métricas — HRV, FC en reposo — se mantienen normales) y
  sugiera evaluación de sobreuso en rodilla.

**6. Fascitis plantar (feb–mar 2025)**
- Caída de horas de entrenamiento (6.6 → 5.0 → 4.5 h/semana) con una subida de peso algo
  mayor que en la lesión de rodilla (menos actividad cruzada posible) y sin el patrón
  sistémico del sobreentrenamiento (HRV/FC en reposo sin cambios relevantes).
- Lo esperable: que la IA la distinga del caso de sobreentrenamiento (por la ausencia de
  caída de HRV/subida de FC en reposo) y del caso de rodilla (por el patrón de peso), y
  sugiera evaluación de dolor en el pie/talón.

## Cómo se sembraron (referencia técnica)

Todo vive en `backend/app/greg_data.py`:
- Los 3 marcadores nuevos/modificados de laboratorio están en `LAB_SERIES` ("Presión
  arterial", "Vitamina D (25-OH)", y los valores de índice 7-9 de "Hemoglobina"/"Ferritina").
- Las 3 anomalías de Garmin están en `_OVERTRAINING_IDX`, `_RUNNERS_KNEE_IDX` y
  `_PLANTAR_FASCIITIS_IDX`, aplicadas como correcciones puntuales sobre la fórmula base
  dentro de `_garmin_events()`.
- Para regenerar estos datos desde cero: borrar al paciente "Greg Welch" (y sus eventos) de
  la base de datos y volver a correr `python -m app.seed_greg`.

## Nota sobre este archivo

Este archivo es intencionalmente la única fuente documental de las 6 anomalías: no se le
pasa a la IA en el prompt de la Fase 3 (`ai_summary.py` solo recibe los eventos crudos del
paciente, nunca este archivo), así que su presencia en el repo no invalida la prueba. Sirve
para que cualquiera que trabaje en el proyecto (incluido un colaborador nuevo) entienda qué
está sembrado ahí y por qué, sin tener que adivinarlo leyendo `greg_data.py` línea por línea.
