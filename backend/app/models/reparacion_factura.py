# backend/app/models/reparacion_factura.py
from typing import Optional, TYPE_CHECKING
from datetime import datetime, timezone

from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import (
    Integer,
    ForeignKey,
    String,
    DateTime,
    Column as SAColumn,
    Index,
)
from pydantic import ConfigDict

#if TYPE_CHECKING:
#    from .reparacion import Reparacion
#    from .usuario import Usuario

if TYPE_CHECKING:
    from .reparacion import Reparacion
    from .usuario import Usuario


class ReparacionFactura(SQLModel, table=True):
    """
    Facturas asociadas a una reparación (N facturas por reparación).
    El fichero se guarda en disco; aquí solo van metadatos y ruta relativa.
    """
    model_config = ConfigDict(from_attributes=True)

    __tablename__ = "reparacion_factura"
    __table_args__ = (
        # índices (los nombres no son críticos mientras usemos Alembic)
        Index("ix_repfact_reparacion", "reparacion_id"),
        Index("ix_repfact_subido_en", "subido_en"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)

    reparacion_id: int = Field(
        sa_column=SAColumn(
            Integer,
            ForeignKey("reparacion.id", ondelete="CASCADE"),
            nullable=False,
        ),
        description="Reparación a la que pertenece la factura",
    )

    # Alias de columna: atributo nombre_archivo -> columna nombre_original
    nombre_archivo: Optional[str] = Field(
        default=None,
        sa_column=SAColumn("nombre_original", String(255), nullable=True),
        description="Nombre original del archivo subido",
    )

    # Alias de columna: atributo ruta_relativa -> columna path_relativo
    ruta_relativa: str = Field(
        sa_column=SAColumn("path_relativo", String(500), nullable=False),
        description="Ruta/nombre relativa dentro del directorio de facturas",
    )

    content_type: Optional[str] = Field(
        default=None,
        sa_column=SAColumn(String(100), nullable=True),
        description="MIME type del archivo",
    )

    tamano_bytes: int = Field(
        sa_column=SAColumn(Integer, nullable=False),
        description="Tamaño del archivo en bytes",
    )

    subido_en: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=SAColumn(DateTime(timezone=True), nullable=False),
        description="Fecha de subida de la factura (UTC)",
    )

    subido_por_id: Optional[int] = Field(
        default=None,
        sa_column=SAColumn(
            Integer,
            ForeignKey("usuario.id", ondelete="SET NULL"),
            nullable=True,
        ),
        description="Usuario que subió la factura",
    )

    # Relaciones ORM
    reparacion: "Reparacion" = Relationship(back_populates="facturas")
    subido_por: Optional["Usuario"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[ReparacionFactura.subido_por_id]"}
    )

    def __repr__(self) -> str:
        return f"<ReparacionFactura {self.id} rep={self.reparacion_id}>"
