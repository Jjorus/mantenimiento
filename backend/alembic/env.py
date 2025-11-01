# alembic/env.py
import sys
from pathlib import Path

# Ajusta el sys.path para poder importar "app.*"
ROOT = Path(__file__).resolve().parents[1]  # ...\backend (carpeta que contiene "app")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from logging.config import fileConfig
from alembic import context
from sqlmodel import SQLModel

# --- Logging de Alembic (alembic.ini) ---
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# --- Tu app: settings y modelos ---
from app.core.config import settings
import app.models  # ¡Importante! registra todos tus modelos en SQLModel.metadata


# Metadata objetivo (para autogenerate)
target_metadata = SQLModel.metadata


def _is_sqlite_url(url: str) -> bool:
    return url.startswith("sqlite")


def _get_db_url() -> str:
    """
    Obtiene la URL de la BD desde settings.
    Evitamos depender del engine global en offline mode.
    """
    return settings.DATABASE_URL


def run_migrations_offline() -> None:
    """
    Modo OFFLINE: no abre conexión, emite SQL a partir de la URL.
    """
    url = _get_db_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
        # En SQLite conviene batch mode para ciertas operaciones ALTER
        render_as_batch=_is_sqlite_url(url),
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Modo ONLINE: abre conexión y corre migraciones con ella.
    Puedes reutilizar tu engine o crear uno aquí.
    """
    # Opción A: reutilizar tu engine global (simple y correcto)
    from app.core.db import get_engine
    engine = get_engine()
    is_sqlite = _is_sqlite_url(str(engine.url))

    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
            render_as_batch=is_sqlite,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
