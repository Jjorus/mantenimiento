# backend/app/models/usuario_adjunto.py
from typing import Optional
from datetime import datetime, timezone

from sqlmodel import SQLModel, Field
from sqlalchemy import Column, Integer, ForeignKey, DateTime, String, func


class UsuarioAdjunto(SQLModel, table=True):
    __tablename__ = "usuario_adjunto"

    id: Optional[int] = Field(default=None, primary_key=True)

    usuario_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("usuario.id", ondelete="CASCADE"),
            nullable=False,
        )
    )

    nombre_archivo: str = Field(sa_column=Column(String(255), nullable=False))
    ruta_relativa: str = Field(sa_column=Column(String(500), nullable=False))
    content_type: Optional[str] = Field(default=None, max_length=100)
    tamano_bytes: Optional[int] = Field(default=None)

    subido_en: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False,
        ),
    )

    subido_por_id: Optional[int] = Field(
        default=None,
        sa_column=Column(
            Integer,
            ForeignKey("usuario.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
