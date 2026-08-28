"""
Configuración de la base de datos.

Usa SQLite por defecto (archivo local, cero configuración) para desarrollo.
Para producción, basta con cambiar DATABASE_URL a Postgres/MySQL — SQLAlchemy
se encarga del resto sin tocar el resto del código.
"""
import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_SQLITE_PATH = BASE_DIR / "salud_deporte.db"

DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{DEFAULT_SQLITE_PATH}")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """Dependencia de FastAPI: una sesión de BD por request, cerrada al final."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
