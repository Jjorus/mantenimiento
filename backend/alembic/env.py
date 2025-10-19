from __future__ import annotations

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]  # ...\backend

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))



from logging.config import fileConfig
from alembic import context
from sqlmodel import SQLModel
# Carga config de alembic.ini
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Importa tu engine y registra modelos
from app.core.db import engine
import app.models  # asegúrate de que importa todos tus modelos

target_metadata = SQLModel.metadata

def run_migrations_offline() -> None:
    url = str(engine.url)
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    connectable = engine
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
