# app/models/ubicacion.py
from typing import Optional, TYPE_CHECKING
from datetime import datetime, timezone

from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey,
    DateTime,
    Index,
    UniqueConstraint,
    func,
)
from pydantic import ConfigDict

if TYPE_CHECKING:
    from .seccion import Seccion
    from .equipo import Equipo


class Ubicacion(SQLModel, table=True):
    """
    Ubicación física o lógica de los equipos.
    - Unicidad por sección + nombre.
    - Timestamps UTC con server_default/onupdate.
    - Índices útiles para listados y búsquedas.
    """
    model_config = ConfigDict(from_attributes=True)

    __table_args__ = (
        # Un nombre de ubicación debe ser único dentro de la misma sección
        UniqueConstraint("seccion_id", "nombre", name="uq_ubicacion_seccion_nombre"),
        # Índices comunes de consulta
        Index("ix_ubicacion_nombre", "nombre"),
        Index("ix_ubicacion_seccion", "seccion_id"),
    )

    # --- PK ---
    id: Optional[int] = Field(default=None, primary_key=True)

    # --- Datos principales ---
    # OJO: usamos sa_column; por eso los índices se definen en __table_args__
    nombre: str = Field(
        sa_column=Column(String(150), nullable=False),
        min_length=2,
        max_length=150,
        description="Nombre visible de la ubicación (único por sección)",
    )

    # ON DELETE SET NULL para no romper referencias si se elimina la sección
    seccion_id: Optional[int] = Field(
        default=None,
        sa_column=Column(
            Integer,
            ForeignKey("seccion.id", ondelete="SET NULL"),
            nullable=True,
        ),
        description="Sección a la que pertenece (opcional)",
    )

    # --- Timestamps (UTC) ---
    creado_en: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
        description="Fecha de creación (UTC)",
    )
    actualizado_en: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False),
        description="Fecha de última actualización (UTC)",
    )

    # --- Relaciones ORM ---
    seccion: Optional["Seccion"] = Relationship(
        back_populates="ubicaciones",
        sa_relationship_kwargs={"foreign_keys": "[Ubicacion.seccion_id]"},
    )

    equipos: list["Equipo"] = Relationship(
        back_populates="ubicacion",
        sa_relationship_kwargs={"passive_deletes": True},
    )

    # --- Utilidades ---
    def __repr__(self) -> str:
        return f"<Ubicacion {self.id} nombre={self.nombre!r} seccion_id={self.seccion_id}>"
