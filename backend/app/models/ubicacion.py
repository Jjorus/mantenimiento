from sqlmodel import SQLModel, Field

class Ubicacion(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    nombre: str
    tipo: str  # ALMACEN/LAB/OBRA/PERSONA/OTRO
