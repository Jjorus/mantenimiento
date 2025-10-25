# backend/app/models/movimiento.py
from typing import Optional, TYPE_CHECKING
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Integer, ForeignKey, Column  # <-- importa Column/Integer/ForeignKey


if TYPE_CHECKING:
    from .equipo import Equipo
    from .ubicacion import Ubicacion

class Movimiento(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    equipo_id: int = Field(sa_column=Column(Integer, ForeignKey("equipo.id", ondelete="CASCADE"), nullable=False, index=True,))
    
    fecha: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)

    desde_ubicacion_id: Optional[int] = Field(default=None, sa_column=Column(Integer, ForeignKey("ubicacion.id", ondelete="SET NULL"), nullable=True, index=True,),)
    
    hacia_ubicacion_id: Optional[int] = Field(default=None, sa_column=Column(Integer, ForeignKey("ubicacion.id", ondelete="SET NULL"), nullable=True, index=True,),)

    comentario: Optional[str] = Field(default=None, max_length=500)

    equipo: "Equipo" = Relationship(back_populates="movimientos", sa_relationship_kwargs={"passive_deletes": True},)

    # Relaciones explícitas a Ubicacion (distinguiendo cada FK)
    desde_ubicacion: Optional["Ubicacion"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[Movimiento.desde_ubicacion_id]"},
    )
    hacia_ubicacion: Optional["Ubicacion"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[Movimiento.hacia_ubicacion_id]"},
    )
