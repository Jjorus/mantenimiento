from typing import Optional, TYPE_CHECKING
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import (
    Integer,
    ForeignKey,
    Column,
    DateTime,
    Index,
    func,
)
from pydantic import ConfigDict

if TYPE_CHECKING:
    from .equipo import Equipo
    from .ubicacion import Ubicacion
    from .usuario import Usuario


class Movimiento(SQLModel, table=True):
    """
    Registro de movimiento de un equipo entre ubicaciones.
    - Timestamps en UTC con server_default (resiliencia si falla el default en app).
    - Índice compuesto (equipo_id, fecha) para historial rápido.
    - Auditoría opcional (usuario_id) usada por los endpoints si existe.
    """
    model_config = ConfigDict(from_attributes=True)

    __table_args__ = (
        Index("ix_movimiento_equipo_fecha", "equipo_id", "fecha"),
        Index("ix_movimiento_fecha", "fecha"),
        # Si necesitas índices para desde/hacia_ubicacion_id:
        Index("ix_movimiento_desde_ubicacion_id", "desde_ubicacion_id"),
        Index("ix_movimiento_hacia_ubicacion_id", "hacia_ubicacion_id"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)

    equipo_id: int = Field(
        sa_column=Column(Integer, ForeignKey("equipo.id", ondelete="CASCADE"), nullable=False),
        description="Equipo movido",
    )

    # Fecha del movimiento (UTC)
    fecha: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
        description="Fecha del movimiento (UTC)",
    )

    # Fecha de última actualización (UTC)
    actualizado_en: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            onupdate=func.now(),
        ),
        description="Fecha de última actualización (UTC)",
    )

    desde_ubicacion_id: Optional[int] = Field(
        default=None,
        sa_column=Column(Integer, ForeignKey("ubicacion.id", ondelete="SET NULL"), nullable=True),
        description="Ubicación origen (puede ser NULL si no aplica)",
    )

    hacia_ubicacion_id: Optional[int] = Field(
        default=None,
        sa_column=Column(Integer, ForeignKey("ubicacion.id", ondelete="SET NULL"), nullable=True),
        description="Ubicación destino (puede ser NULL si no aplica)",
    )

    comentario: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Comentario opcional del movimiento",
    )

    # --- Auditoría ---
    usuario_id: Optional[int] = Field(
        default=None,
        sa_column=Column(Integer, ForeignKey("usuario.id", ondelete="SET NULL"), nullable=True),
        description="Usuario que ejecutó el movimiento (si se registra)",
    )

    # --- Relaciones ORM ---
    equipo: "Equipo" = Relationship(
        back_populates="movimientos",
        sa_relationship_kwargs={"passive_deletes": True},
    )

    # Relaciones explícitas a Ubicación (distinguiendo cada FK)
    desde_ubicacion: "Optional[Ubicacion]" = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[Movimiento.desde_ubicacion_id]"},
    )
    
    hacia_ubicacion: "Optional[Ubicacion]" = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[Movimiento.hacia_ubicacion_id]"},
    )

    # Relación con usuario que realizó el movimiento
    usuario: "Optional[Usuario]" = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[Movimiento.usuario_id]"}
    )

    # --- Métodos útiles ---
    def __repr__(self) -> str:
        return f"<Movimiento {self.id} equipo={self.equipo_id} {self.desde_ubicacion_id}->{self.hacia_ubicacion_id}>"

    @property
    def es_reciente(self) -> bool:
        """Determina si el movimiento es reciente (menos de 24 horas)."""
        if not self.fecha:
            return False
        delta = datetime.now(timezone.utc) - self.fecha
        return delta.days < 1

    @property
    def descripcion_ubicaciones(self) -> str:
        """Descripción legible del movimiento entre ubicaciones."""
        desde = f"Ubicación {self.desde_ubicacion_id}" if self.desde_ubicacion_id else "Origen desconocido"
        hacia = f"Ubicación {self.hacia_ubicacion_id}" if self.hacia_ubicacion_id else "Destino desconocido"
        return f"De {desde} a {hacia}"

    @property
    def tiene_comentario(self) -> bool:
        """Verifica si el movimiento tiene comentario."""
        return bool(self.comentario and self.comentario.strip())

    def obtener_resumen(self) -> dict:
        """Devuelve un resumen estructurado del movimiento."""
        return {
            "id": self.id,
            "equipo_id": self.equipo_id,
            "fecha": self.fecha.isoformat() if self.fecha else None,
            "desde_ubicacion_id": self.desde_ubicacion_id,
            "hacia_ubicacion_id": self.hacia_ubicacion_id,
            "usuario_id": self.usuario_id,
            "es_reciente": self.es_reciente,
            "tiene_comentario": self.tiene_comentario,
        }
