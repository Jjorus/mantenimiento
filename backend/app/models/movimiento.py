from __future__ import annotations
from typing import Optional, TYPE_CHECKING
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from .equipo import Equipo
    from .ubicacion import Ubicacion

class Movimiento(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    equipo_id: int = Field(foreign_key="equipo.id", index=True)
    fecha: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)

    desde_ubicacion_id: Optional[int] = Field(default=None, foreign_key="ubicacion.id", index=True)
    hacia_ubicacion_id: Optional[int] = Field(default=None, foreign_key="ubicacion.id", index=True)

    comentario: Optional[str] = Field(default=None, max_length=500)

    equipo: "Equipo" = Relationship(back_populates="movimientos")

    # Relaciones explícitas a Ubicacion (distinguiendo cada FK)
    desde_ubicacion: "Ubicacion | None" = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[Movimiento.desde_ubicacion_id]"},
    )
    hacia_ubicacion: "Ubicacion | None" = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[Movimiento.hacia_ubicacion_id]"},
    )
