"""
Configuración de la app leída de variables de entorno / archivo .env.

No se debe poner ninguna llave directamente en el código — siempre vía
variables de entorno, para que nunca terminen en el repositorio de git.
"""
import os
from pathlib import Path

try:
    from dotenv import load_dotenv

    # Busca ".env" en la raíz del proyecto (un nivel arriba de backend/).
    load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")
except ImportError:
    # python-dotenv es opcional: si no está instalado, igual funciona si la
    # variable de entorno ya está definida a nivel del sistema operativo.
    pass

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929").strip()

AI_CONFIGURED = bool(ANTHROPIC_API_KEY)
