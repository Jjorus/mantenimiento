# ubicacion.py
from typing import Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship, Column
from sqlalchemy import Integer, ForeignKey

if TYPE_CHECKING:
    from .seccion import Seccion
    from .equipo import Equipo

class Ubicacion(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str = Field(index=True, min_length=2, max_length=150)

    # ON DELETE SET NULL
    seccion_id: Optional[int] = Field(
        default=None,
        
        sa_column=Column(Integer, ForeignKey("seccion.id", ondelete="SET NULL"), nullable=True, index=True),
    )
    seccion: Optional["Seccion"] = Relationship(back_populates="ubicaciones")

    equipos: list["Equipo"] = Relationship(back_populates="ubicacion")
