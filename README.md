# Gestión Salud y Deporte

Aplicación web personal para organizar información de salud (y, más adelante, deportiva)
bajo las categorías del estándar internacional **HL7 FHIR**. Es el punto de partida de un
proyecto más grande: una app que cualquier persona pueda usar para llevar su información de
salud organizada, que eventualmente pueda integrarse con instituciones médicas, y sobre la
cual se pueda construir un motor de IA que correlacione datos y genere alertas y planes de
salud personalizados.

Este repositorio es la primera fase: **la base de datos y la app web funcionando en tu
computador**, cargada ya con tu registro de salud actual.

La app soporta más de un paciente cargado a la vez (por ejemplo, tus datos reales y un
paciente de prueba) — un selector en la parte superior deja elegir cuál está activo; la
elección se recuerda en una cookie del navegador.

## Arranque rápido (Windows)

1. Asegúrate de tener [Python 3.11+](https://www.python.org/downloads/) instalado (marca
   "Add Python to PATH" durante la instalación).
2. Haz doble clic en `run_windows.bat` (o ejecútalo desde una terminal en esta carpeta).
3. El script crea un entorno virtual, instala las dependencias, carga tus datos iniciales
   la primera vez, y abre `http://127.0.0.1:8000` en tu navegador.

## Arranque manual (cualquier sistema operativo)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # en Windows: .venv\Scripts\activate
pip install -r ../requirements.txt

python -m app.seed               # carga tu registro de salud inicial (solo la primera vez)
uvicorn app.main:app --reload    # arranca el servidor
```

Luego abre `http://127.0.0.1:8000` — vas a ver un panel con tus datos organizados por
categoría FHIR, una vista de todos los eventos (filtrable), y un formulario para agregar
eventos nuevos a mano. La documentación interactiva de la API está en
`http://127.0.0.1:8000/docs`.

## Importar una foto con IA (Fase 1)

La opción "Importar foto" del menú te deja subir la foto de un resultado, una orden médica o
un carné de vacunación — la IA lee el contenido y te muestra un formulario prellenado para
que lo confirmes antes de guardar (nada se guarda solo).

Para activarla necesitas tu propia llave de la API de Anthropic:

1. Consigue una llave en [console.anthropic.com/settings/keys](https://console.anthropic.com/settings/keys).
2. Copia `.env.example` a un archivo nuevo llamado `.env` (en la raíz del proyecto).
3. Abre `.env` y pega tu llave en `ANTHROPIC_API_KEY=`.
4. Reinicia la app (`run_windows.bat` de nuevo, o `Ctrl+C` y volver a correr `uvicorn`).

El archivo `.env` está en `.gitignore` — tu llave nunca se sube al repositorio.

## Tendencias en el tiempo (Fase 2)

La opción "Tendencias" del menú grafica la evolución de cualquier prueba que tenga al menos
dos registros con fecha exacta y valor numérico (por ejemplo, tu colesterol total bajando de
265 a 137 mg/dL). El rango de referencia se muestra como una banda de fondo cuando se puede
interpretar del texto del registro. Chart.js va incluido localmente
(`backend/app/static/vendor/`) — no depende de ningún servicio externo para dibujar la
gráfica.

## Paciente de prueba: Greg Welch (para seguir desarrollando)

En una instalación nueva, además de tu registro real, la app carga un segundo paciente
sintético: **Greg Welch**, un triatleta amateur de 40 años con 5 años (2021-2025) de
historial de laboratorio (10 paneles, 14 marcadores) y datos mensuales estilo Garmin
(VO2max, FC en reposo, HRV, horas de entrenamiento, sueño, peso). Sirve como set de datos
realista para seguir construyendo funcionalidad sin tocar tu información real — se
identifica en el selector de paciente como "(prueba)".

Sus datos viven en `backend/app/greg_data.py` y se cargan con `python -m app.seed_greg`
(ya incluido en `run_windows.bat` en una instalación nueva). El detalle de qué condiciones
de salud y deportivas están sembradas deliberadamente en sus datos — para poner a prueba el
resumen con IA de la Fase 3 — está en
[`docs/ANOMALIAS_PRUEBA_GREG.md`](docs/ANOMALIAS_PRUEBA_GREG.md).

## Resumen interpretativo con IA (Fase 3)

La opción "Resumen IA" del menú envía todo el historial del paciente activo a la API de
Claude y devuelve un análisis en español: una impresión general, una lista de hallazgos
(cada uno con un nivel — importante / atención / informativo — y, cuando aplica, la gráfica
del marcador que lo respalda), sugerencias generales, y temas concretos para comentarle al
médico. Usa la misma `ANTHROPIC_API_KEY` que la importación por foto (Fase 1) — no requiere
configuración adicional si ya la tienes activa.

**Esto no es un diagnóstico médico** — es una lectura interpretativa de tus propios datos
pensada para ayudarte a decidir qué vale la pena comentarle a tu médico tratante. El aviso
aparece siempre, de forma fija, en la página.

Mientras se genera el resumen (puede tardar medio minuto o más) se muestra un indicador de
carga con un contador de segundos, para que quede claro que la app sigue trabajando.

## Correr las pruebas

```bash
cd backend
pytest
```

## Estructura del proyecto

```
GestionSaludDeporte/
├── backend/
│   ├── app/
│   │   ├── main.py           # arranque de la app FastAPI
│   │   ├── database.py       # conexión a la base de datos (SQLite por defecto)
│   │   ├── models.py         # tablas (Patient, HealthEvent con categorías FHIR)
│   │   ├── schemas.py        # validación de datos de entrada/salida (Pydantic)
│   │   ├── crud.py           # funciones de acceso a datos
│   │   ├── seed.py           # carga tu registro de salud inicial
│   │   ├── ai_extract.py     # lee una foto con Claude y la estructura en HealthEvent
│   │   ├── ai_summary.py     # arma el prompt y llama a Claude para el resumen interpretativo (Fase 3)
│   │   ├── config.py         # lee ANTHROPIC_API_KEY y demás variables de entorno
│   │   ├── trends.py         # interpreta "value"/"reference_range" como números para graficar
│   │   ├── greg_data.py      # datos sintéticos de 5 años del paciente de prueba Greg Welch
│   │   ├── seed_greg.py      # carga a Greg Welch (idempotente)
│   │   ├── routers/          # rutas de la API JSON y de las páginas web (incluye summary.py, Fase 3)
│   │   ├── templates/        # páginas HTML (Jinja2, incluye resumen.html)
│   │   └── static/           # CSS + Chart.js local (vendor/)
│   └── tests/                # pruebas automáticas (pytest)
├── docs/
│   ├── ARQUITECTURA.md              # decisiones de diseño y hoja de ruta hacia IA/multiusuario
│   └── ANOMALIAS_PRUEBA_GREG.md     # clave de respuestas de las anomalías sembradas en Greg Welch
├── requirements.txt
├── .env.example               # plantilla — copiar a .env y pegar tu llave ahí
└── run_windows.bat
```

## Hoja de ruta

Ver [`docs/ARQUITECTURA.md`](docs/ARQUITECTURA.md) para el detalle técnico y las siguientes
fases: exportación FHIR real, multiusuario, y el motor de correlación con IA para alertas y
planes de salud.

## Aviso

Esta aplicación organiza información que tú ya posees; no reemplaza la historia clínica
oficial ni el criterio médico. Antes de tomar decisiones clínicas con base en estos datos,
verifícalos contra el documento original de la institución correspondiente.
