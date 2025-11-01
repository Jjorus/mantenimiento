# backend/app/models/seccion.py
from typing import Optional, TYPE_CHECKING
from datetime import datetime, timezone

from sqlmodel import SQLModel, Field, Relationship, Column
from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import CITEXT  # requiere extensión 'citext'
from pydantic import ConfigDict

if TYPE_CHECKING:
    from .ubicacion import Ubicacion
    from .equipo import Equipo


class Seccion(SQLModel, table=True):
    """
    Sección/área a la que pertenecen equipos y ubicaciones.
    - 'nombre' único case-insensitive (CITEXT, PostgreSQL).
    - Timestamps en UTC con server_default / onupdate.
    """
    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = Field(default=None, primary_key=True)

    # Unicidad case-insensitive en PG (CITEXT). No añadas index=True aquí:
    # ya habrá un índice implícito por UNIQUE.
    nombre: str = Field(
        description="Nombre único de la sección (case-insensitive)",
        sa_column=Column(CITEXT(), unique=True, nullable=False),
        min_length=2,
        max_length=150,
    )

    # Timestamps (UTC)
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

    # Relaciones
    # Nota: Ubicacion.seccion ya tiene back_populates="ubicaciones"
    ubicaciones: list["Ubicacion"] = Relationship(back_populates="seccion")

    # En Equipo definiste: seccion: Relationship(..., sin back_populates)
    # Para evitar desajustes, dejamos la relación de "equipos" sin back_populates.
    equipos: list["Equipo"] = Relationship()

    def __repr__(self) -> str:
        return f"<Seccion id={self.id} nombre={self.nombre!r}>"
