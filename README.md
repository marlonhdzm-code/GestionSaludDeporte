# Gestión Salud y Deporte

Aplicación web personal para organizar información de salud (y, más adelante, deportiva)
bajo las categorías del estándar internacional **HL7 FHIR**. Es el punto de partida de un
proyecto más grande: una app que cualquier persona pueda usar para llevar su información de
salud organizada, que eventualmente pueda integrarse con instituciones médicas, y sobre la
cual se pueda construir un motor de IA que correlacione datos y genere alertas y planes de
salud personalizados.

Este repositorio es la primera fase: **la base de datos y la app web funcionando en tu
computador**, cargada ya con tu registro de salud actual.

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
│   │   ├── config.py         # lee ANTHROPIC_API_KEY y demás variables de entorno
│   │   ├── routers/          # rutas de la API JSON y de las páginas web
│   │   ├── templates/        # páginas HTML (Jinja2)
│   │   └── static/           # CSS
│   └── tests/                # pruebas automáticas (pytest)
├── docs/
│   └── ARQUITECTURA.md       # decisiones de diseño y hoja de ruta hacia IA/multiusuario
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
