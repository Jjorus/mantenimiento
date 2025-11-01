# backend/app/models/reparacion.py
from typing import Optional, TYPE_CHECKING
from datetime import datetime, timezone

from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import (
    Integer,
    ForeignKey,
    DateTime,
    String,
    Text,
    CheckConstraint,
    Index,
    func,
    Column as SAColumn,
)
from pydantic import ConfigDict

if TYPE_CHECKING:
    from .equipo import Equipo
    from .usuario import Usuario


class Reparacion(SQLModel, table=True):
    """
    Reparaciones realizadas a un equipo.
    - Estado validado en BD (check constraint).
    - Timestamps en UTC con server_default / onupdate.
    - Auditoría: creador, último modificador y (si aplica) quién cierra.
    - Índices para consultas habituales.
    """
    model_config = ConfigDict(from_attributes=True)

    __table_args__ = (
        CheckConstraint(
            "estado in ('ABIERTA','EN_PROGRESO','CERRADA')",
            name="ck_reparacion_estado",
        ),
        Index("ix_reparacion_equipo_fecha_inicio", "equipo_id", "fecha_inicio"),
        Index("ix_reparacion_estado_fecha_inicio", "estado", "fecha_inicio"),
    )

    # --- PK ---
    id: Optional[int] = Field(default=None, primary_key=True)

    # --- Relaciones obligatorias ---
    # Nota: no usar index=True cuando se pasa sa_column
    equipo_id: int = Field(
        sa_column=SAColumn(
            Integer,
            ForeignKey("equipo.id", ondelete="CASCADE"),
            nullable=False,
        ),
        description="Equipo reparado",
    )

    # --- Fechas (UTC) ---
    fecha_inicio: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=SAColumn(DateTime(timezone=True), server_default=func.now(), nullable=False),
        description="Fecha de inicio de la reparación (UTC)",
    )

    fecha_fin: Optional[datetime] = Field(
        default=None,
        sa_column=SAColumn(DateTime(timezone=True), nullable=True),
        description="Fecha de fin/cierre de la reparación (UTC, si aplica)",
    )

    creado_en: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=SAColumn(DateTime(timezone=True), server_default=func.now(), nullable=False),
        description="Marca de creación (UTC)",
    )

    actualizado_en: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=SAColumn(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False),
        description="Última actualización (UTC)",
    )

    # --- Contenido ---
    titulo: str = Field(
        sa_column=SAColumn(String(150), nullable=False),
        min_length=3,
        max_length=150,
        description="Título/causa breve",
    )

    descripcion: Optional[str] = Field(
        default=None,
        sa_column=SAColumn(Text, nullable=True),
        max_length=4000,
        description="Descripción detallada del trabajo realizado",
    )

    estado: str = Field(
        default="ABIERTA",
        sa_column=SAColumn(String(20), nullable=False),
        max_length=20,
        description="Estado: ABIERTA | EN_PROGRESO | CERRADA",
    )

    # --- Auditoría ---
    usuario_id: Optional[int] = Field(
        default=None,
        sa_column=SAColumn(Integer, ForeignKey("usuario.id", ondelete="SET NULL"), nullable=True),
        description="Usuario que creó la reparación",
    )

    usuario_modificador_id: Optional[int] = Field(
        default=None,
        sa_column=SAColumn(Integer, ForeignKey("usuario.id", ondelete="SET NULL"), nullable=True),
        description="Último usuario que modificó la reparación",
    )

    cerrada_por_id: Optional[int] = Field(
        default=None,
        sa_column=SAColumn(Integer, ForeignKey("usuario.id", ondelete="SET NULL"), nullable=True),
        description="Usuario que cerró la reparación (si aplica)",
    )

    # --- Relaciones ORM ---
    equipo: "Equipo" = Relationship(
        back_populates="reparaciones",
        sa_relationship_kwargs={"passive_deletes": True},
    )

    usuario: Optional["Usuario"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[Reparacion.usuario_id]"}
    )
    usuario_modificador: Optional["Usuario"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[Reparacion.usuario_modificador_id]"}
    )
    cerrada_por: Optional["Usuario"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[Reparacion.cerrada_por_id]"}
    )

    # --- Métodos de dominio ---
    def __repr__(self) -> str:
        return f"<Reparacion {self.id} eq={self.equipo_id} ({self.estado})>"

    @property
    def es_cerrable(self) -> bool:
        """Determina si la reparación puede cerrarse."""
        return self.estado in {"ABIERTA", "EN_PROGRESO"}

    @property
    def duracion_dias(self) -> Optional[int]:
        """
        Días naturales entre fecha_inicio y fecha_fin.
        Si no está cerrada, devuelve None.
        """
        if not self.fecha_fin or not self.fecha_inicio:
            return None
        return (self.fecha_fin - self.fecha_inicio).days

    def cerrar(self, usuario_id: int) -> None:
        """Cierra la reparación aplicando reglas de dominio y auditoría."""
        if self.estado == "CERRADA":
            raise ValueError("La reparación ya está cerrada")
        if not self.es_cerrable:
            raise ValueError(f"No se puede cerrar una reparación en estado {self.estado}")

        self.estado = "CERRADA"
        self.fecha_fin = datetime.now(timezone.utc)
        self.cerrada_por_id = usuario_id
        self.usuario_modificador_id = usuario_id

    def reabrir(self, usuario_id: int) -> None:
        """Reabre una reparación cerrada (elimina marca de cierre)."""
        if self.estado != "CERRADA":
            raise ValueError("Solo se pueden reabrir reparaciones cerradas")

        self.estado = "ABIERTA"
        self.fecha_fin = None
        self.cerrada_por_id = None
        self.usuario_modificador_id = usuario_id
