# backend/app/models/equipo.py
from typing import Optional, TYPE_CHECKING
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey,
    DateTime,
    CheckConstraint,
    Index,
    func,
)
from pydantic import ConfigDict, field_validator

if TYPE_CHECKING:
    from .seccion import Seccion
    from .ubicacion import Ubicacion
    from .movimiento import Movimiento
    from .incidencia import Incidencia
    from .reparacion import Reparacion


class Equipo(SQLModel, table=True):
    """
    Equipo de calibración / instrumento gestionado.
    - Normaliza identidad y nfc_tag a minúsculas (también aquí, no solo en el router).
    - Estados validados en BD (CHECK).
    - Timestamps en UTC con server_default / onupdate.
    - Índices pensados para tus consultas más frecuentes.
    - Unicidad case-insensitive reforzada con índices funcionales (Alembic).
    """
    model_config = ConfigDict(from_attributes=True)

    __table_args__ = (
        # Estados válidos
        CheckConstraint(
            "estado in ('OPERATIVO','MANTENIMIENTO','BAJA','CALIBRACION','RESERVA')",
            name="ck_equipo_estado",
        ),
        # Índices útiles
        Index("ix_equipo_identidad", "identidad"),
        Index("ix_equipo_nfc_tag", "nfc_tag"),
        Index("ix_equipo_estado", "estado"),
        Index("ix_equipo_tipo", "tipo"),
        Index("ix_equipo_estado_tipo", "estado", "tipo"),
        Index("ix_equipo_seccion_id", "seccion_id"),
        Index("ix_equipo_ubicacion_id", "ubicacion_id"),
    )

    # --- PK ---
    id: Optional[int] = Field(default=None, primary_key=True)

    # --- Identificadores ---
    # La unicidad case-insensitive se crea en Alembic con índices únicos funcionales.
    identidad: Optional[str] = Field(
        default=None,
        sa_column=Column(String(100), nullable=True),
        description="Identificador visible (se normaliza a minúsculas)",
    )
    numero_serie: Optional[str] = Field(
        default=None,
        sa_column=Column(String(150), nullable=True),
        description="Número de serie del fabricante",
    )

    # --- Clasificación / estado ---
    tipo: str = Field(
        sa_column=Column(String(100), nullable=False),
        description="Tipo: Calibrador, Multímetro, etc.",
    )
    estado: str = Field(
        default="OPERATIVO",
        sa_column=Column(String(20), nullable=False),
        description="OPERATIVO | MANTENIMIENTO | BAJA | CALIBRACION | RESERVA",
    )

    # --- Relaciones lógicas ---
    seccion_id: Optional[int] = Field(
        default=None,
        sa_column=Column(Integer, ForeignKey("seccion.id", ondelete="SET NULL"), nullable=True),
        description="Sección a la que pertenece",
    )
    ubicacion_id: Optional[int] = Field(
        default=None,
        sa_column=Column(Integer, ForeignKey("ubicacion.id", ondelete="SET NULL"), nullable=True),
        description="Ubicación actual (almacén, zona, operario, etc.)",
    )

    # Tag NFC asociado (normalizado a minúsculas)
    nfc_tag: Optional[str] = Field(
        default=None,
        sa_column=Column(String(64), nullable=True),
        description="Identificador NFC (se normaliza a minúsculas)",
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
    seccion: Optional["Seccion"] = Relationship(sa_relationship_kwargs={"foreign_keys": "[Equipo.seccion_id]"})
    ubicacion: Optional["Ubicacion"] = Relationship(sa_relationship_kwargs={"foreign_keys": "[Equipo.ubicacion_id]"})

    movimientos: list["Movimiento"] = Relationship(
        back_populates="equipo",
        sa_relationship_kwargs={"passive_deletes": True},
    )
    incidencias: list["Incidencia"] = Relationship(
        back_populates="equipo",
        sa_relationship_kwargs={"passive_deletes": True},
    )
    reparaciones: list["Reparacion"] = Relationship(
        back_populates="equipo",
        sa_relationship_kwargs={"passive_deletes": True},
    )

    # --- Validadores (Pydantic v2) ---
    @field_validator("identidad", "nfc_tag", mode="before")
    @classmethod
    def _to_lower_or_none(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v2 = v.strip()
        return v2.lower() if v2 else None

    # --- Utilidades ---
    def __repr__(self) -> str:
        return f"<Equipo {self.id} identidad={self.identidad} estado={self.estado} tipo={self.tipo}>"

    @property
    def tiene_ubicacion(self) -> bool:
        return self.ubicacion_id is not None

    @property
    def tiene_seccion(self) -> bool:
        return self.seccion_id is not None

    @property
    def tiene_nfc(self) -> bool:
        return self.nfc_tag is not None

    @property
    def puede_moverse(self) -> bool:
        return self.estado in {"OPERATIVO", "RESERVA"}

    @property
    def necesita_atencion(self) -> bool:
        return self.estado in {"MANTENIMIENTO", "CALIBRACION"}

    @property
    def esta_operativo(self) -> bool:
        return self.estado == "OPERATIVO"

    def obtener_info_resumen(self) -> dict:
        return {
            "id": self.id,
            "identidad": self.identidad,
            "numero_serie": self.numero_serie,
            "tipo": self.tipo,
            "estado": self.estado,
            "ubicacion_id": self.ubicacion_id,
            "seccion_id": self.seccion_id,
            "nfc_tag": self.nfc_tag,
            "tiene_ubicacion": self.tiene_ubicacion,
            "tiene_seccion": self.tiene_seccion,
            "tiene_nfc": self.tiene_nfc,
            "puede_moverse": self.puede_moverse,
            "necesita_atencion": self.necesita_atencion,
            "esta_operativo": self.esta_operativo,
            "creado_en": self.creado_en.isoformat() if self.creado_en else None,
            "actualizado_en": self.actualizado_en.isoformat() if self.actualizado_en else None,
        }

    def puede_ser_eliminado(self) -> bool:
        # La validación real la hace la BD a través de FKs y se captura en el endpoint.
        return True
