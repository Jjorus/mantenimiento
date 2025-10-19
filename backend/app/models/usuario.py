from sqlmodel import SQLModel, Field

class Usuario(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    password_hash: str
    role: str = Field(default="OPERARIO")   # ADMIN/MANTENIMIENTO/OPERARIO
    active: bool = Field(default=True)
