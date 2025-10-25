# backend/app/models/seccion.py
from typing import Optional, TYPE_CHECKING

from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column 
from sqlalchemy.dialects.postgresql import CITEXT  # requiere extensión citext

if TYPE_CHECKING:
    from .ubicacion import Ubicacion
    from .equipo import Equipo


class Seccion(SQLModel, table=True):
    """
    Sección/área a la que pertenecen equipos y ubicaciones.
    'nombre' es único sin distinguir mayúsculas/minúsculas (CITEXT).
    """
    id: Optional[int] = Field(default=None, primary_key=True)

    # Unicidad + índice case-insensitive con CITEXT (PostgreSQL)
    nombre: str = Field(
        description="Nombre único de la sección (case-insensitive)",
        sa_column=Column(CITEXT(), unique=True, nullable=False),
    )

    # Relaciones
    ubicaciones: list["Ubicacion"] = Relationship(back_populates="seccion")
    equipos: list["Equipo"] = Relationship(back_populates="seccion")

    def __repr__(self) -> str:
        return f"<Seccion id={self.id} nombre={self.nombre!r}>"
