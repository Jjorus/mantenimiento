# app/models/usuario.py
from typing import Optional
from datetime import datetime, timezone

from sqlmodel import SQLModel, Field
from sqlalchemy import (
    Column,
    String,
    Boolean,
    Integer,
    DateTime,
    CheckConstraint,
    Index,
    func,
)
from sqlalchemy.dialects.postgresql import CITEXT  # requiere extensión citext
from pydantic import ConfigDict


class Usuario(SQLModel, table=True):
    """
    Modelo de usuario con seguridad reforzada:
    - username/email en CITEXT (únicos, case-insensitive)
    - control de bloqueos por fuerza bruta
    - MFA opcional (TOTP)
    - marcas de auditoría (created/updated/last_login/password_changed)
    """
    model_config = ConfigDict(from_attributes=True)

    __table_args__ = (
        # Roles permitidos
        CheckConstraint(
            "role in ('ADMIN','MANTENIMIENTO','OPERARIO')",
            name="ck_usuario_role",
        ),
        # Contadores y coherencia de flags
        CheckConstraint(
            "failed_login_count >= 0",
            name="ck_usuario_failed_login_nonneg",
        ),
        # Índices útiles para administración/reporting
        Index("ix_usuario_role_active", "role", "active"),
        Index("ix_usuario_created_at", "created_at"),
        Index("ix_usuario_last_login_at", "last_login_at"),
    )

    # --- Identidad ---
    id: Optional[int] = Field(default=None, primary_key=True)

    # username único (case-insensitive gracias a CITEXT)
    username: str = Field(
        sa_column=Column(CITEXT(), unique=True, nullable=False),
        min_length=3,
        max_length=64,
        description="Nombre de usuario único (case-insensitive)",
    )

    # email opcional pero único si se informa (case-insensitive)
    email: Optional[str] = Field(
        default=None,
        sa_column=Column(CITEXT(), unique=True, nullable=True),
        description="Email del usuario (opcional, único si existe)",
    )

    # nombre visible para UI (no único)
    display_name: Optional[str] = Field(
        default=None,
        sa_column=Column(String(120), nullable=True),
        description="Nombre para mostrar",
    )

    # --- Seguridad / Estado ---
    password_hash: str = Field(
        sa_column=Column(String(255), nullable=False),
        min_length=20,
        max_length=255,
        description="Hash Argon2id o equivalente",
    )

    role: str = Field(
        default="OPERARIO",
        sa_column=Column(String(20), nullable=False),
        description="ADMIN | MANTENIMIENTO | OPERARIO",
    )

    active: bool = Field(
        default=True,
        sa_column=Column(Boolean, nullable=False, server_default="true"),
        description="Si el usuario puede autenticarse",
    )

    # MFA (TOTP)
    mfa_enabled: bool = Field(
        default=False,
        sa_column=Column(Boolean, nullable=False, server_default="false"),
        description="Si tiene MFA TOTP activado",
    )
    totp_secret: Optional[str] = Field(
        default=None,
        sa_column=Column(String(64), nullable=True),
        description="Secreto TOTP (cuando MFA está activo)",
    )

    # Anti fuerza bruta / bloqueo temporal
    failed_login_count: int = Field(
        default=0,
        sa_column=Column(Integer, nullable=False, server_default="0"),
        description="Intentos fallidos acumulados",
    )
    locked_until: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
        description="Bloqueado hasta (UTC) si aplica",
    )

    # --- Auditoría / Tiempos ---
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False, server_default=func.now()),
        description="Creado (UTC)",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()),
        description="Última actualización (UTC)",
    )
    last_login_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
        description="Último login exitoso (UTC)",
    )
    password_changed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False, server_default=func.now()),
        description="Cuándo se cambió la contraseña por última vez",
    )

    # --- Utilidades (no guardan estado) ---
    def __repr__(self) -> str:
        return f"<Usuario {self.id} {self.username} role={self.role} active={self.active}>"

    def safe_profile(self) -> dict:
        """Perfil seguro para respuestas (sin campos sensibles)."""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "display_name": self.display_name,
            "role": self.role,
            "active": self.active,
            "mfa_enabled": self.mfa_enabled,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
            "password_changed_at": self.password_changed_at.isoformat() if self.password_changed_at else None,
        }
