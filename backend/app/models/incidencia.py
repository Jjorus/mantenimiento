# incidencia.py
from typing import Optional, TYPE_CHECKING
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import CheckConstraint, Column, Integer, ForeignKey

if TYPE_CHECKING:
    from .equipo import Equipo

class Incidencia(SQLModel, table=True):
    __table_args__ = (
        # Garantiza estado válido a nivel BD (si no usas Enum)
        CheckConstraint(
            "estado in ('ABIERTA','EN_PROGRESO','CERRADA')",
            name="ck_incidencia_estado"
        ),
    )

    id: Optional[int] = Field(default=None, primary_key=True)

    equipo_id: int = Field(sa_column=Column(Integer, ForeignKey("equipo.id", ondelete="CASCADE"), nullable=False, index=True))
    
    fecha: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)

    titulo: str = Field(min_length=3, max_length=150)
    
    descripcion: Optional[str] = Field(default=None, max_length=2000)

    # Si prefieres validación en Pydantic:
    estado: str = Field(default="ABIERTA", max_length=20, index=True)

    equipo: "Equipo" = Relationship(back_populates="incidencias", sa_relationship_kwargs={"passive_deletes": True})
