# backend/app/models/reparacion.py
from typing import Optional, TYPE_CHECKING
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import CheckConstraint, Integer, ForeignKey, Column
from sqlalchemy.types import Numeric

if TYPE_CHECKING:
    from .equipo import Equipo


class Reparacion(SQLModel, table=True):
    __table_args__ = (
        # coste >= 0 a nivel BD (permite NULL)
        CheckConstraint("coste IS NULL OR coste >= 0", name="ck_reparacion_coste_ge_0"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)

    # FK a equipo con borrado en cascada
    equipo_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("equipo.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )

    # Índices para consultas por fecha
    fecha_inicio: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)
    fecha_fin: Optional[datetime] = None

    titulo: Optional[str] = Field(default=None, max_length=120)
    descripcion: str = Field(min_length=1, max_length=2000)

    # Decimal en BD (NUMERIC(10,2))
    coste: Optional[float] = Field(default=None, sa_column=Column(Numeric(10, 2)))

    # Si quieres validar estados a nivel BD, puedes añadir un CheckConstraint como en incidencia.
    estado: str = Field(default="ABIERTA", max_length=20, index=True)

    equipo: "Equipo" = Relationship(
        back_populates="reparaciones",
        sa_relationship_kwargs={"passive_deletes": True},
    )
