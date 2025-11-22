# app/core/db.py
from typing import Generator, Optional
from contextlib import contextmanager

from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy.pool import StaticPool
from app.core.config import settings


def _build_engine():
    """
    Construye un motor SQLAlchemy/SQLModel con parámetros sacados de settings.
    - Postgres/MySQL: aplica pre_ping y pooling configurable.
    - SQLite: maneja connect_args y pool apropiado (especialmente en memoria).
    """
    url: str = settings.DATABASE_URL
    echo: bool = bool(getattr(settings, "DB_ECHO", False))

    # SQLite (file o memoria)
    if url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
        kwargs = dict(echo=echo, connect_args=connect_args, future=True)

        # En memoria → usa StaticPool para compartir conexión en el proceso (tests)
        if ":memory:" in url:
            kwargs["poolclass"] = StaticPool

        engine = create_engine(url, **kwargs)
        return engine

    # Postgres/MySQL (ej. postgresql+psycopg://)
    pool_size = getattr(settings, "DB_POOL_SIZE", 5)
    max_overflow = getattr(settings, "DB_MAX_OVERFLOW", 10)
    pool_recycle = getattr(settings, "DB_POOL_RECYCLE", 3600)
    pool_timeout = getattr(settings, "DB_POOL_TIMEOUT", 30)

    engine = create_engine(
        url,
        echo=echo,
        future=True,
        pool_pre_ping=True,          # evita conexiones muertas
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_recycle=pool_recycle,
        pool_timeout=pool_timeout,
    )
    return engine


# Motor global (singleton)
engine = _build_engine()


def init_db() -> None:
    """
    Inicializa el esquema en DEV si no usas Alembic.
    En STAGING/PROD, **no** crea tablas: usa migraciones (alembic upgrade head).
    """
    import app.models  # registra todos los modelos en SQLModel.metadata

    if settings.is_development:
        # En dev puede ser útil crear tablas automáticamente
        SQLModel.metadata.create_all(engine)
    # En staging/prod, deja que Alembic gestione el esquema.


def get_engine():
    """Devuelve el engine por si se requiere en scripts o tests."""
    return engine


def get_session() -> Generator[Session, None, None]:
    """
    Dependencia para FastAPI (yield).
    """
    with Session(engine) as session:
        yield session


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """
    Context manager conveniente para scripts/migraciones manuales:

        with session_scope() as s:
            ... do stuff ...
    """
    s: Optional[Session] = None
    try:
        s = Session(engine)
        yield s
        s.commit()
    except Exception:
        if s is not None:
            s.rollback()
        raise
    finally:
        if s is not None:
            s.close()
