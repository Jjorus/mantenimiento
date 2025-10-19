# app/core/db.py
from typing import Generator
from sqlmodel import SQLModel, create_engine, Session
from app.core.config import settings  # <-- IMPORTA settings

def _build_engine():
    url = settings.DATABASE_URL
    echo = bool(getattr(settings, "DB_ECHO", False))
    # Si usas SQLite, añade connect_args; con Postgres no hace falta
    if url.startswith("sqlite"):
        return create_engine(url, echo=echo, connect_args={"check_same_thread": False})
    # Para Postgres/MySQL, pre_ping evita conexiones muertas
    return create_engine(url, echo=echo, pool_pre_ping=True)

engine = _build_engine()

def init_db() -> None:
    """
    Crea las tablas si no existen.
    Asegúrate de importar tus modelos antes de crear metadata.
    """
    import app.models  # noqa: F401  (registra tus modelos en SQLModel.metadata)
    SQLModel.metadata.create_all(engine)  # <-- ahora SQLModel se “usa” y no avisa el linter

def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
