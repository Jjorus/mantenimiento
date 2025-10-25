from __future__ import annotations
from typing import Optional, Any, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship, Column, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import Integer, ForeignKey

if TYPE_CHECKING:
    from .seccion import Seccion
    from .ubicacion import Ubicacion
    from .reparacion import Reparacion
    from .incidencia import Incidencia
    from .movimiento import Movimiento

class Equipo(SQLModel, table=True):
    __table_args__ = (
        UniqueConstraint("identidad", name="uq_equipo_identidad"),
        UniqueConstraint("nfc_tag", name="uq_equipo_nfc_tag"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)

    identidad: str = Field(index=True, min_length=2, max_length=64)
    numero_serie: Optional[str] = Field(default=None, index=True, max_length=128)
    nfc_tag: Optional[str] = Field(default=None, index=True)

    # ON DELETE SET NULL (Seccion y Ubicacion pueden borrarse dejando el campo a NULL)
    seccion_id: Optional[int] = Field(
        default=None,
        
        sa_column=Column(Integer, ForeignKey("seccion.id", ondelete="SET NULL"), nullable=True, index=True,),
    )
    ubicacion_id: Optional[int] = Field(
        default=None,
        
        sa_column=Column(Integer, ForeignKey("ubicacion.id", ondelete="SET NULL"), nullable=True, index=True,),
    )

    seccion: "Seccion | None" = Relationship(back_populates="equipos", sa_relationship_kwargs={"passive_deletes": True})
    ubicacion: "Ubicacion | None" = Relationship(back_populates="equipos", sa_relationship_kwargs={"passive_deletes": True})

    atributos: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))

    reparaciones: list["Reparacion"] = Relationship(back_populates="equipo")
    incidencias:  list["Incidencia"]  = Relationship(back_populates="equipo")
    movimientos:  list["Movimiento"]  = Relationship(back_populates="equipo")
