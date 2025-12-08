# backend/app/models/reparacion.py
from typing import Optional, TYPE_CHECKING, List
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
    UniqueConstraint,
    Numeric,
    func,
    Column as SAColumn,
)
from pydantic import ConfigDict, computed_field

if TYPE_CHECKING:
    from .equipo import Equipo
    from .usuario import Usuario
    from .incidencia import Incidencia
    from .reparacion_factura import ReparacionFactura
    from .reparacion_gasto import ReparacionGasto


class Reparacion(SQLModel, table=True):
    """
    Reparaciones realizadas a un equipo.
    - Siempre vinculadas a una incidencia previa (incidencia_id).
    - Estado validado en BD (check constraint).
    - Timestamps en UTC con server_default / onupdate.
    - Auditoría: creador, último modificador y (si aplica) quién cierra.
    - Costes y datos de factura básicos.
    - Índices para consultas habituales.
    """
    model_config = ConfigDict(from_attributes=True)

    __table_args__ = (
        CheckConstraint(
            "estado in ('ABIERTA','EN_PROGRESO','CERRADA')",
            name="ck_reparacion_estado",
        ),
        # Solo una reparación por equipo+incidencia
        UniqueConstraint("equipo_id", "incidencia_id", name="uq_reparacion_equipo_incidencia"),
        Index("ix_reparacion_equipo_fecha_inicio", "equipo_id", "fecha_inicio"),
        Index("ix_reparacion_estado_fecha_inicio", "estado", "fecha_inicio"),
        Index("ix_reparacion_incidencia", "incidencia_id"),
    )

    # --- PK ---
    id: Optional[int] = Field(default=None, primary_key=True)

    # --- Relaciones obligatorias ---
    equipo_id: int = Field(
        sa_column=SAColumn(
            Integer,
            ForeignKey("equipo.id", ondelete="CASCADE"),
            nullable=False,
        ),
        description="Equipo reparado",
    )

    incidencia_id: int = Field(
        sa_column=SAColumn(
            Integer,
            ForeignKey("incidencia.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        description="Incidencia de origen de la reparación",
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

    # --- Costes y facturación ---
    coste_materiales: Optional[float] = Field(
        default=None,
        sa_column=SAColumn(Numeric(10, 2), nullable=True),
        description="Coste de materiales en la moneda indicada",
    )
    coste_mano_obra: Optional[float] = Field(
        default=None,
        sa_column=SAColumn(Numeric(10, 2), nullable=True),
        description="Coste de mano de obra en la moneda indicada",
    )
    coste_otros: Optional[float] = Field(
        default=None,
        sa_column=SAColumn(Numeric(10, 2), nullable=True),
        description="Otros costes (transporte, tasas, etc.)",
    )
    moneda: Optional[str] = Field(
        default="EUR",
        sa_column=SAColumn(String(3), nullable=True, server_default="EUR"),
        min_length=3,
        max_length=3,
        description="Código de moneda ISO (ej. EUR, USD)",
    )
    proveedor: Optional[str] = Field(
        default=None,
        sa_column=SAColumn(String(150), nullable=True),
        description="Proveedor / taller que realizó el servicio",
    )
    numero_factura: Optional[str] = Field(
        default=None,
        sa_column=SAColumn(String(50), nullable=True),
        description="Número de factura asociado (campo genérico)",
    )

    # Metadatos de archivo de factura PRINCIPAL (para compatibilidad)
    factura_archivo_nombre: Optional[str] = Field(
        default=None,
        sa_column=SAColumn(String(255), nullable=True),
        description="Nombre original del archivo de factura principal",
    )
    factura_archivo_path: Optional[str] = Field(
        default=None,
        sa_column=SAColumn(String(500), nullable=True),
        description="Ruta relativa donde se guarda el archivo principal en el servidor",
    )
    factura_content_type: Optional[str] = Field(
        default=None,
        sa_column=SAColumn(String(100), nullable=True),
        description="MIME type del archivo subido (application/pdf, image/jpeg, etc.)",
    )
    factura_tamano_bytes: Optional[int] = Field(
        default=None,
        sa_column=SAColumn(Integer, nullable=True),
        description="Tamaño del archivo de factura principal en bytes",
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

    incidencia: "Incidencia" = Relationship(
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

    # N facturas asociadas
    facturas: List["ReparacionFactura"] = Relationship(
        back_populates="reparacion",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )

    # --- Métodos de dominio ---
    def __repr__(self) -> str:
        return f"<Reparacion {self.id} eq={self.equipo_id} ({self.estado})>"

    @property
    def es_cerrable(self) -> bool:
        """Determina si la reparación puede cerrarse."""
        return self.estado in {"ABIERTA", "EN_PROGRESO"}

    @computed_field  # type: ignore[misc]
    @property
    def duracion_dias(self) -> Optional[int]:
        """
        Días naturales entre fecha_inicio y fecha_fin.
        Si no está cerrada, devuelve None.
        """
        if not self.fecha_fin or not self.fecha_inicio:
            return None
        return (self.fecha_fin - self.fecha_inicio).days

    @computed_field  # type: ignore[misc]
    @property
    def coste_total(self) -> Optional[float]:
        """
        Coste total aproximado (materiales + mano de obra + otros).
        Si todo es None, devuelve None.
        """
        partes = [
            self.coste_materiales or 0,
            self.coste_mano_obra or 0,
            self.coste_otros or 0,
        ]
        if all(v == 0 for v in partes):
            return None
        return float(sum(partes))

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

    gastos: list["ReparacionGasto"] = Relationship(back_populates="reparacion", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
