"""seccion: citext unique; reparacion: estados/indices/auditoria + utc

Revision ID: b3393d72c463
Revises: c9385816ede8
Create Date: 2025-11-01 21:33:59.627412
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "b3393d72c463"
down_revision = "c9385816ede8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- Asegurar extensión citext (idempotente) ---
    op.execute("CREATE EXTENSION IF NOT EXISTS citext;")

    # =========================
    #  SECCION
    # =========================
    # Convertir 'nombre' a CITEXT (si no lo está). Requiere USING en algunos casos.
    # Si ya es citext, el ALTER puede fallar: lo envolvemos en try/except implícito con SQL simple.
    try:
        op.execute("ALTER TABLE seccion ALTER COLUMN nombre TYPE citext;")
    except Exception:
        # ya era citext o el motor no necesita conversión
        pass

    # Asegurar UNIQUE de nombre (si ya existe, ignorar error)
    try:
        op.create_unique_constraint("uq_seccion_nombre", "seccion", ["nombre"])
    except Exception:
        pass

    # Índice auxiliar (no único) por nombre para ordenaciones/búsquedas
    try:
        op.create_index("ix_seccion_nombre", "seccion", ["nombre"], unique=False)
    except Exception:
        pass

    # Timestamps en seccion (si no estaban)
    try:
        op.add_column(
            "seccion",
            sa.Column(
                "creado_en",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
        )
    except Exception:
        pass

    try:
        op.add_column(
            "seccion",
            sa.Column(
                "actualizado_en",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
        )
    except Exception:
        pass

    # =========================
    #  REPARACION
    # =========================
    # Auditoría y timestamps (si faltan)
    for colname in ("creado_en", "actualizado_en"):
        try:
            op.add_column(
                "reparacion",
                sa.Column(
                    colname,
                    sa.DateTime(timezone=True),
                    server_default=sa.text("now()"),
                    nullable=False,
                ),
            )
        except Exception:
            pass

    # Usuarios de auditoría (si faltan)
    for colname in ("usuario_id", "usuario_modificador_id", "cerrada_por_id"):
        try:
            op.add_column("reparacion", sa.Column(colname, sa.Integer(), nullable=True))
        except Exception:
            pass

    # Fechas a timestamptz + server_default en fecha_inicio
    try:
        op.alter_column(
            "reparacion",
            "fecha_inicio",
            existing_type=postgresql.TIMESTAMP(),
            type_=sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            existing_nullable=False,
        )
    except Exception:
        pass

    try:
        op.alter_column(
            "reparacion",
            "fecha_fin",
            existing_type=postgresql.TIMESTAMP(),
            type_=sa.DateTime(timezone=True),
            existing_nullable=True,
        )
    except Exception:
        pass

    # Ajustes de longitudes/tipos de texto
    try:
        op.alter_column(
            "reparacion",
            "titulo",
            existing_type=sa.VARCHAR(length=120),
            type_=sa.String(length=150),
            nullable=False,
        )
    except Exception:
        pass

    try:
        op.alter_column(
            "reparacion",
            "descripcion",
            existing_type=sa.VARCHAR(length=2000),
            type_=sa.Text(),
            nullable=True,
        )
    except Exception:
        pass

    # Índices compuestos (recreamos modernos y retiramos antiguos si existen)
    # Primero quitamos antiguos en caso de que sigan:
    for old_idx in ("ix_reparacion_equipo_id", "ix_reparacion_estado", "ix_reparacion_fecha_inicio"):
        try:
            op.drop_index(old_idx, table_name="reparacion")
        except Exception:
            pass

    # Nuevos índices
    try:
        op.create_index(
            "ix_reparacion_equipo_fecha_inicio",
            "reparacion",
            ["equipo_id", "fecha_inicio"],
            unique=False,
        )
    except Exception:
        pass

    try:
        op.create_index(
            "ix_reparacion_estado_fecha_inicio",
            "reparacion",
            ["estado", "fecha_inicio"],
            unique=False,
        )
    except Exception:
        pass

    # FKs de auditoría (SET NULL). Si ya existen, ignora.
    try:
        op.create_foreign_key(
            "rep_usuario_fk",
            "reparacion",
            "usuario",
            ["usuario_id"],
            ["id"],
            ondelete="SET NULL",
        )
    except Exception:
        pass

    try:
        op.create_foreign_key(
            "rep_usuario_modificador_fk",
            "reparacion",
            "usuario",
            ["usuario_modificador_id"],
            ["id"],
            ondelete="SET NULL",
        )
    except Exception:
        pass

    try:
        op.create_foreign_key(
            "rep_cerrada_por_fk",
            "reparacion",
            "usuario",
            ["cerrada_por_id"],
            ["id"],
            ondelete="SET NULL",
        )
    except Exception:
        pass

    # FK a equipo con ON DELETE CASCADE:
    # Intentamos soltar una posible FK antigua con nombre estándar;
    # si el nombre fue distinto, esto no fallará la migración por el try/except
    for fkname in ("rep_equipo_fk", "reparacion_equipo_id_fkey"):
        try:
            op.drop_constraint(fkname, "reparacion", type_="foreignkey")
        except Exception:
            pass

    try:
        op.create_foreign_key(
            "rep_equipo_fk",
            "reparacion",
            "equipo",
            ["equipo_id"],
            ["id"],
            ondelete="CASCADE",
        )
    except Exception:
        pass

    # Check constraint de estados válidos (si no existe)
    try:
        op.create_check_constraint(
            "ck_reparacion_estado",
            "reparacion",
            "estado in ('ABIERTA','EN_PROGRESO','CERRADA')",
        )
    except Exception:
        pass

    # NOTA: mantenemos 'coste' si existía. NO lo borramos aquí.
    # Si realmente quieres eliminar 'coste', añade:
    #   op.drop_column("reparacion", "coste")
    # y en downgrade vuelve a crearlo.


def downgrade() -> None:
    # ========== REPARACION ==========
    # FKs
    for fkname in ("rep_equipo_fk", "rep_cerrada_por_fk", "rep_usuario_modificador_fk", "rep_usuario_fk"):
        try:
            op.drop_constraint(fkname, "reparacion", type_="foreignkey")
        except Exception:
            pass

    # Índices
    for idx in ("ix_reparacion_estado_fecha_inicio", "ix_reparacion_equipo_fecha_inicio"):
        try:
            op.drop_index(idx, table_name="reparacion")
        except Exception:
            pass

    # Columnas de auditoría/timestamps
    for colname in ("cerrada_por_id", "usuario_modificador_id", "usuario_id", "actualizado_en", "creado_en"):
        try:
            op.drop_column("reparacion", colname)
        except Exception:
            pass

    # Tipos (volver atrás) — opcional, normalmente no revertimos timestamptz
    try:
        op.alter_column(
            "reparacion",
            "descripcion",
            existing_type=sa.Text(),
            type_=sa.VARCHAR(length=2000),
            nullable=False,
        )
    except Exception:
        pass

    try:
        op.alter_column(
            "reparacion",
            "titulo",
            existing_type=sa.String(length=150),
            type_=sa.VARCHAR(length=120),
            nullable=True,
        )
    except Exception:
        pass

    # ========== SECCION ==========
    # Índice + UNIQUE
    try:
        op.drop_index("ix_seccion_nombre", table_name="seccion")
    except Exception:
        pass
    try:
        op.drop_constraint("uq_seccion_nombre", "seccion", type_="unique")
    except Exception:
        pass

    # Timestamps
    for colname in ("actualizado_en", "creado_en"):
        try:
            op.drop_column("seccion", colname)
        except Exception:
            pass

    # No desinstalamos la extensión citext por seguridad.
