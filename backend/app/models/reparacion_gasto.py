from typing import Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from .reparacion import Reparacion

class ReparacionGasto(SQLModel, table=True):
    # CORRECCIÓN: Nombre en singular para mantener consistencia
    __tablename__ = "reparacion_gasto"

    id: Optional[int] = Field(default=None, primary_key=True)
    
    # CORRECCIÓN: 'reparacion.id' en singular (coincide con la tabla creada por Reparacion)
    reparacion_id: int = Field(foreign_key="reparacion.id", nullable=False)
    
    descripcion: str = Field(nullable=False)
    importe: float = Field(default=0.0)
    tipo: str = Field(default="MATERIALES")  # 'MATERIALES', 'MANO_OBRA', 'OTROS'

    reparacion: Optional["Reparacion"] = Relationship(back_populates="gastos")