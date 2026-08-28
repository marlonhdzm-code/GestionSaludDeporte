@echo off
REM Arranca la app en Windows. Doble clic o ejecutar desde la carpeta del proyecto.
cd /d "%~dp0backend"

if not exist ".venv" (
    echo Creando entorno virtual...
    python -m venv .venv
)

call .venv\Scripts\activate.bat

echo Instalando dependencias...
pip install -q -r ..\requirements.txt

if not exist "salud_deporte.db" (
    echo Cargando datos iniciales...
    python -m app.seed
)

echo.
echo Abriendo en http://127.0.0.1:8000
start http://127.0.0.1:8000
uvicorn app.main:app --reload
