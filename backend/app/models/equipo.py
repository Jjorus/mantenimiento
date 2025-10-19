from sqlmodel import SQLModel, Field

class Equipo(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    codigo: str = Field(index=True, unique=True)
    numero_serie: str | None = Field(default=None, index=True)
    tipo: str
    estado: str = Field(default="OPERATIVO")
    ubicacion_actual_id: int | None = Field(default=None, foreign_key="ubicacion.id")
    atributos: dict | None = None
