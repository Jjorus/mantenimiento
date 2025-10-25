from __future__ import annotations
from typing import Optional, TYPE_CHECKING, Literal
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field, Relationship, Column
from sqlalchemy import CheckConstraint
from sqlalchemy.types import Numeric

if TYPE_CHECKING:
    from .equipo import Equipo

class Reparacion(SQLModel, table=True):
    __table_args__ = (
        # coste >= 0 a nivel BD
        CheckConstraint("coste IS NULL OR coste >= 0", name="ck_reparacion_coste_ge_0"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)

    equipo_id: int = Field(foreign_key="equipo.id", index=True)

    # Índices para consultas por fecha
    fecha_inicio: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)
    fecha_fin: datetime | None = None

    titulo: str | None = Field(default=None, max_length=120)
    descripcion: str = Field(min_length=1, max_length=2000)

    # Decimal en BD (NUMERIC(10,2))
    coste: float | None = Field(default=None, sa_column=Column(Numeric(10, 2)))

    estado: str = Field(default="ABIERTA", max_length=20, index=True)

    equipo: "Equipo" = Relationship(back_populates="reparaciones")
