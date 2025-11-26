# backend/app/models/incidencia_adjunto.py
from typing import Optional
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, Integer, ForeignKey, DateTime, String, func

class IncidenciaAdjunto(SQLModel, table=True):
    __tablename__ = "incidencia_adjunto"

    id: Optional[int] = Field(default=None, primary_key=True)
    
    incidencia_id: int = Field(
        sa_column=Column(Integer, ForeignKey("incidencia.id", ondelete="CASCADE"), nullable=False)
    )
    
    # Metadatos del archivo
    nombre_archivo: str = Field(sa_column=Column(String(255), nullable=False))
    ruta_relativa: str = Field(sa_column=Column(String(500), nullable=False))
    content_type: Optional[str] = Field(default=None, max_length=100)
    tamano_bytes: Optional[int] = Field(default=None)
    
    subido_en: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    )
    
    subido_por_id: Optional[int] = Field(
        default=None,
        sa_column=Column(Integer, ForeignKey("usuario.id", ondelete="SET NULL"), nullable=True)
    )

    # Nota: Si quisieras relaciones inversas, deberías añadirlas en incidencia.py y usuario.py
    # Por ahora funciona perfectamente así para la API.