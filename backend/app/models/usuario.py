
# app/models/usuario.py
from typing import Optional
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field, Column
from sqlalchemy import CheckConstraint
from sqlalchemy.dialects.postgresql import CITEXT  # necesita la extensión citext

class Usuario(SQLModel, table=True):
    __table_args__ = (
        CheckConstraint(
            "role in ('ADMIN','MANTENIMIENTO','OPERARIO')",
            name="ck_usuario_role",
        ),
    )

    id: Optional[int] = Field(default=None, primary_key=True)

    # OJO: sin index=True porque ya usamos sa_column
    username: str = Field(
        min_length=3,
        max_length=64,
        sa_column=Column(CITEXT(), unique=True, nullable=False),
        description="Nombre de usuario único (no distingue mayúsc/minúsculas)",
    )

    password_hash: str = Field(min_length=20, max_length=255)
    role: str = Field(default="OPERARIO", max_length=20, index=True)
    active: bool = Field(default=True, index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
