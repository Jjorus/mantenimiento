# app/models/ubicacion.py
from typing import Optional, TYPE_CHECKING
from datetime import datetime, timezone

from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey,
    DateTime,
    Index,
    UniqueConstraint,
    CheckConstraint,
    func,
)
from pydantic import ConfigDict

if TYPE_CHECKING:
    from .seccion import Seccion
    from .equipo import Equipo
    from .movimiento import Movimiento  # <- para hints
    from .usuario import Usuario        # <- NUEVO: relación con usuario técnico


class Ubicacion(SQLModel, table=True):
    """
    Ubicación física o lógica de los equipos.
    - Unicidad por sección + nombre.
    - Timestamps UTC con server_default/onupdate.
    - Índices útiles para listados y búsquedas.
    - Puede estar asociada a un usuario (técnico) cuando tipo='TECNICO'.
    """
    model_config = ConfigDict(from_attributes=True)

    __table_args__ = (
        UniqueConstraint("seccion_id", "nombre", name="uq_ubicacion_seccion_nombre"),
        Index("ix_ubicacion_nombre", "nombre"),
        Index("ix_ubicacion_seccion", "seccion_id"),
        CheckConstraint(
            "tipo in ('ALMACEN','LABORATORIO','TECNICO','OTRO')",
            name="ck_ubicacion_tipo",
        ),
    )

    id: Optional[int] = Field(default=None, primary_key=True)

    nombre: str = Field(
        sa_column=Column(String(150), nullable=False),
        min_length=2,
        max_length=150,
        description="Nombre visible de la ubicación (único por sección)",
    )

    seccion_id: Optional[int] = Field(
        default=None,
        sa_column=Column(
            Integer,
            ForeignKey("seccion.id", ondelete="SET NULL"),
            nullable=True,
        ),
        description="Sección a la que pertenece (opcional)",
    )

    # --- Clasificación de la ubicación ---
    tipo: str = Field(
        default="OTRO",
        sa_column=Column(
            String(20),
            nullable=False,
            server_default="OTRO",
        ),
        description="Tipo lógico: ALMACEN|LABORATORIO|TECNICO|OTRO",
    )

    # Si es una ubicación personal de técnico, enlaza al usuario
    usuario_id: Optional[int] = Field(
        default=None,
        sa_column=Column(
            Integer,
            ForeignKey("usuario.id", ondelete="SET NULL"),
            nullable=True,
            unique=True,  # cada usuario técnico sólo puede tener una ubicación asociada
        ),
        description="Usuario asociado cuando la ubicación representa a un técnico",
    )

    # --- Timestamps (UTC) ---
    creado_en: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
        description="Fecha de creación (UTC)",
    )
    actualizado_en: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False),
        description="Fecha de última actualización (UTC)",
    )

    # --- Relaciones ORM ---
    seccion: Optional["Seccion"] = Relationship(
        back_populates="ubicaciones",
        sa_relationship_kwargs={"foreign_keys": "[Ubicacion.seccion_id]"},
    )

    equipos: list["Equipo"] = Relationship(
        back_populates="ubicacion",
        sa_relationship_kwargs={"passive_deletes": True},
    )

    # Nuevas relaciones para enlazar con Movimiento (doble FK)
    movimientos_entrada: list["Movimiento"] = Relationship(
        back_populates="hacia_ubicacion",
        sa_relationship_kwargs={
            "foreign_keys": "[Movimiento.hacia_ubicacion_id]",
            "primaryjoin": "Ubicacion.id==Movimiento.hacia_ubicacion_id",
        },
    )
    movimientos_salida: list["Movimiento"] = Relationship(
        back_populates="desde_ubicacion",
        sa_relationship_kwargs={
            "foreign_keys": "[Movimiento.desde_ubicacion_id]",
            "primaryjoin": "Ubicacion.id==Movimiento.desde_ubicacion_id",
        },
    )

    # NUEVA relación inversa hacia Usuario (ubicación de técnico)
    usuario: Optional["Usuario"] = Relationship(
        back_populates="ubicacion_asociada",
        sa_relationship_kwargs={"foreign_keys": "[Ubicacion.usuario_id]"},
    )

    def __repr__(self) -> str:
        return (
            f"<Ubicacion {self.id} nombre={self.nombre!r} "
            f"seccion_id={self.seccion_id} tipo={self.tipo!r} usuario_id={self.usuario_id}>"
        )
