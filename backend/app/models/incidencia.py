# backend/app/models/incidencia.py
from typing import Optional, TYPE_CHECKING
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import (
    CheckConstraint,
    Column,
    Integer,
    ForeignKey,
    DateTime,
    Index,
    String,
    Text,
    func,
)
from pydantic import ConfigDict

if TYPE_CHECKING:
    from .equipo import Equipo
    from .usuario import Usuario
    from .reparacion import Reparacion


class Incidencia(SQLModel, table=True):
    """
    Incidencias sobre un equipo.
    - Estado validado en BD (check constraint) y en la API (Literal en los endpoints).
    - Timestamps en UTC.
    - Auditoría completa (usuario creador / último modificador / quien cerró).
    """
    model_config = ConfigDict(from_attributes=True)

    __table_args__ = (
        # Estados válidos (si no usas Enum)
        CheckConstraint(
            "estado in ('ABIERTA','EN_PROGRESO','CERRADA')",
            name="ck_incidencia_estado",
        ),
        # Índices para listas y filtros
        Index("ix_incidencia_equipo_fecha", "equipo_id", "fecha"),
        Index("ix_incidencia_estado_fecha", "estado", "fecha"),
        Index("ix_incidencia_equipo_estado_fecha", "equipo_id", "estado", "fecha"),
    )

    # --- Clave primaria ---
    id: Optional[int] = Field(default=None, primary_key=True)

    # --- Relaciones obligatorias ---
    equipo_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("equipo.id", ondelete="CASCADE"),
            nullable=False,
        ),
        description="Equipo al que pertenece la incidencia",
    )

    # --- Fechas (UTC) ---
    fecha: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
        description="Fecha de creación (UTC)",
    )

    # Última actualización (UTC) - se actualiza en BD automáticamente
    actualizada_en: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            onupdate=func.now(),
        ),
        description="Fecha de última actualización (UTC)",
    )

    # --- Contenido ---
    titulo: str = Field(
        sa_column=Column(String(150), nullable=False),  # VARCHAR(150) en BD
        min_length=3,
        max_length=150,
        description="Título corto de la incidencia",
    )

    descripcion: Optional[str] = Field(
        default=None,
        sa_column=Column(Text, nullable=True),  # TEXT sin límite en BD
        max_length=2000,  # validación API
        description="Descripción detallada (hasta ~2000 caracteres recomendado)",
    )

    # --- Estado ---
    estado: str = Field(
        default="ABIERTA",
        sa_column=Column(String(20), nullable=False),
        max_length=20,
        description="Estado: ABIERTA | EN_PROGRESO | CERRADA",
    )

    # --- Ciclo de vida de cierre ---
    cerrada_en: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
        description="Marca temporal de cierre (UTC, si se cerró)",
    )

    cerrada_por_id: Optional[int] = Field(
        default=None,
        sa_column=Column(Integer, ForeignKey("usuario.id", ondelete="SET NULL"), nullable=True),
        description="Usuario que cerró la incidencia (si aplica)",
    )

    # --- Auditoría ---
    usuario_id: Optional[int] = Field(
        default=None,
        sa_column=Column(Integer, ForeignKey("usuario.id", ondelete="SET NULL"), nullable=True),
        description="Usuario que creó la incidencia",
    )

    usuario_modificador_id: Optional[int] = Field(
        default=None,
        sa_column=Column(Integer, ForeignKey("usuario.id", ondelete="SET NULL"), nullable=True),
        description="Último usuario que modificó la incidencia",
    )

    # --- Relaciones ORM ---
    equipo: "Equipo" = Relationship(
        back_populates="incidencias",
        sa_relationship_kwargs={"passive_deletes": True},
    )

    # 🔹 NUEVA RELACIÓN CON REPARACIONES (lo que faltaba)
    reparaciones: list["Reparacion"] = Relationship(
        back_populates="incidencia",
        sa_relationship_kwargs={"passive_deletes": True},
    )

    # Relaciones con usuarios
    usuario: Optional["Usuario"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[Incidencia.usuario_id]"}
    )

    usuario_modificador: Optional["Usuario"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[Incidencia.usuario_modificador_id]"}
    )

    cerrada_por: Optional["Usuario"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[Incidencia.cerrada_por_id]"}
    )

    # --- Métodos útiles ---
    def __repr__(self) -> str:
        return f"<Incidencia {self.id}: {self.titulo} ({self.estado})>"

    @property
    def es_cerrable(self) -> bool:
        """Determina si la incidencia puede cerrarse (no está ya CERRADA)."""
        return self.estado in {"ABIERTA", "EN_PROGRESO"}

    @property
    def dias_abierta(self) -> Optional[int]:
        """Días desde la creación (si hay fecha)."""
        if not self.fecha:
            return None
        delta = datetime.now(timezone.utc) - self.fecha
        return delta.days

    @property
    def tiempo_resolucion_dias(self) -> Optional[int]:
        """Días hasta la resolución (si está cerrada)."""
        if not self.cerrada_en or not self.fecha:
            return None
        delta = self.cerrada_en - self.fecha
        return delta.days

    def cerrar(self, usuario_id: int) -> None:
        """Cierra la incidencia de manera controlada."""
        if self.estado == "CERRADA":
            raise ValueError("Incidencia ya está cerrada")
        if not self.es_cerrable:
            raise ValueError(f"No se puede cerrar una incidencia en estado {self.estado}")
        self.estado = "CERRADA"
        self.cerrada_en = datetime.now(timezone.utc)
        self.cerrada_por_id = usuario_id
        self.usuario_modificador_id = usuario_id

    def reabrir(self, usuario_id: int) -> None:
        """Reabre una incidencia cerrada."""
        if self.estado != "CERRADA":
            raise ValueError("Solo se pueden reabrir incidencias cerradas")
        self.estado = "ABIERTA"
        self.cerrada_en = None
        self.cerrada_por_id = None
        self.usuario_modificador_id = usuario_id
