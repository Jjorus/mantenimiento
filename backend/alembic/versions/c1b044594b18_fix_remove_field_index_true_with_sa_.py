"""fix: normalize equipo/incidencia/movimiento + indices robustos

Revision ID: c1b044594b18
Revises: 91c8bf68af41
Create Date: 2025-10-27 00:21:08.509387
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "c1b044594b18"
down_revision = "91c8bf68af41"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -----------------------------
    # EQUIPO
    # -----------------------------
    # Añadimos columnas nuevas con server_default para no romper en tablas con datos.
    op.add_column(
        "equipo",
        sa.Column("tipo", sa.String(length=100), nullable=True, server_default="Otro"),
    )
    op.add_column(
        "equipo",
        sa.Column("estado", sa.String(length=20), nullable=True, server_default="OPERATIVO"),
    )
    op.add_column(
        "equipo",
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.add_column(
        "equipo",
        sa.Column(
            "actualizado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # Ajustes de longitud en columnas existentes
    op.alter_column(
        "equipo",
        "identidad",
        existing_type=sa.VARCHAR(length=64),
        type_=sa.String(length=100),
        nullable=True,  # ahora permitimos NULL (la API normaliza)
    )
    op.alter_column(
        "equipo",
        "numero_serie",
        existing_type=sa.VARCHAR(length=128),
        type_=sa.String(length=150),
        existing_nullable=True,
    )

    # Intentamos eliminar columnas/índices/uniques antiguos si existen
    try:
        op.drop_index(op.f("ix_equipo_numero_serie"), table_name="equipo")
    except Exception:
        pass
    try:
        op.drop_constraint(op.f("uq_equipo_identidad"), "equipo", type_="unique")
    except Exception:
        pass
    try:
        op.drop_constraint(op.f("uq_equipo_nfc_tag"), "equipo", type_="unique")
    except Exception:
        pass
    # En algunos esquemas antiguos podría existir 'atributos' (JSONB); si no existe, ignorar
    try:
        op.drop_column("equipo", "atributos")
    except Exception:
        pass

    # Crear índices nuevos
    op.create_index("ix_equipo_estado", "equipo", ["estado"], unique=False)
    op.create_index("ix_equipo_estado_tipo", "equipo", ["estado", "tipo"], unique=False)
    op.create_index("ix_equipo_tipo", "equipo", ["tipo"], unique=False)

    # Backfill defensivo por si hay filas NULL (no debería por server_default, pero garantizamos)
    op.execute("UPDATE equipo SET tipo = 'Otro' WHERE tipo IS NULL;")
    op.execute("UPDATE equipo SET estado = 'OPERATIVO' WHERE estado IS NULL;")

    # Ahora sí, NOT NULL y quitamos default para que la app controle los valores
    op.alter_column("equipo", "tipo", nullable=False, server_default=None)
    op.alter_column("equipo", "estado", nullable=False, server_default=None)

    # -----------------------------
    # INCIDENCIA
    # -----------------------------
    op.add_column(
        "incidencia",
        sa.Column(
            "actualizada_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
    )
    op.add_column(
        "incidencia",
        sa.Column("cerrada_en", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "incidencia",
        sa.Column("cerrada_por_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "incidencia",
        sa.Column("usuario_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "incidencia",
        sa.Column("usuario_modificador_id", sa.Integer(), nullable=True),
    )

    # Ajuste de tipos/defectos
    op.alter_column(
        "incidencia",
        "fecha",
        existing_type=postgresql.TIMESTAMP(),
        server_default=sa.text("now()"),
        type_=sa.DateTime(timezone=True),
        nullable=True,  # permitimos NULL por compatibilidad, la app siempre setea
    )
    op.alter_column(
        "incidencia",
        "descripcion",
        existing_type=sa.VARCHAR(length=2000),
        type_=sa.Text(),
        existing_nullable=True,
    )

    # ÍNDICES: eliminamos antiguos si existen y creamos nuevos combinados
    for idx in (
        op.f("ix_incidencia_equipo_id"),
        op.f("ix_incidencia_estado"),
        op.f("ix_incidencia_fecha"),
    ):
        try:
            op.drop_index(idx, table_name="incidencia")
        except Exception:
            pass

    op.create_index(
        "ix_incidencia_equipo_estado_fecha",
        "incidencia",
        ["equipo_id", "estado", "fecha"],
        unique=False,
    )
    op.create_index(
        "ix_incidencia_equipo_fecha",
        "incidencia",
        ["equipo_id", "fecha"],
        unique=False,
    )
    op.create_index(
        "ix_incidencia_estado_fecha",
        "incidencia",
        ["estado", "fecha"],
        unique=False,
    )

    # FKs de auditoría (con try/except para idempotencia)
    try:
        op.create_foreign_key(
            "inc_usuario_modificador_fk",
            source_table="incidencia",
            referent_table="usuario",
            local_cols=["usuario_modificador_id"],
            remote_cols=["id"],
            ondelete="SET NULL",
        )
    except Exception:
        pass
    try:
        op.create_foreign_key(
            "inc_cerrada_por_fk",
            source_table="incidencia",
            referent_table="usuario",
            local_cols=["cerrada_por_id"],
            remote_cols=["id"],
            ondelete="SET NULL",
        )
    except Exception:
        pass
    try:
        op.create_foreign_key(
            "inc_usuario_fk",
            source_table="incidencia",
            referent_table="usuario",
            local_cols=["usuario_id"],
            remote_cols=["id"],
            ondelete="SET NULL",
        )
    except Exception:
        pass

    # -----------------------------
    # MOVIMIENTO
    # -----------------------------
    op.add_column(
        "movimiento",
        sa.Column(
            "actualizado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
    )
    op.add_column(
        "movimiento",
        sa.Column("usuario_id", sa.Integer(), nullable=True),
    )
    op.alter_column(
        "movimiento",
        "fecha",
        existing_type=postgresql.TIMESTAMP(),
        server_default=sa.text("now()"),
        type_=sa.DateTime(timezone=True),
        nullable=True,
    )

    # Índices
    try:
        op.drop_index(op.f("ix_movimiento_equipo_id"), table_name="movimiento")
    except Exception:
        pass
    op.create_index(
        "ix_movimiento_equipo_fecha",
        "movimiento",
        ["equipo_id", "fecha"],
        unique=False,
    )

    # FK a usuario (auditoría)
    try:
        op.create_foreign_key(
            "mov_usuario_fk",
            source_table="movimiento",
            referent_table="usuario",
            local_cols=["usuario_id"],
            remote_cols=["id"],
            ondelete="SET NULL",
        )
    except Exception:
        pass


def downgrade() -> None:
    # Downgrade best-effort (revierte los cambios más relevantes)
    # MOVIMIENTO
    try:
        op.drop_constraint("mov_usuario_fk", "movimiento", type_="foreignkey")
    except Exception:
        pass
    try:
        op.drop_index("ix_movimiento_equipo_fecha", table_name="movimiento")
    except Exception:
        pass
    try:
        op.alter_column(
            "movimiento",
            "fecha",
            existing_type=sa.DateTime(timezone=True),
            server_default=None,
            type_=postgresql.TIMESTAMP(),
            nullable=False,
        )
    except Exception:
        pass
    try:
        op.drop_column("movimiento", "usuario_id")
    except Exception:
        pass
    try:
        op.drop_column("movimiento", "actualizado_en")
    except Exception:
        pass

    # INCIDENCIA
    for idx in (
        "ix_incidencia_estado_fecha",
        "ix_incidencia_equipo_fecha",
        "ix_incidencia_equipo_estado_fecha",
    ):
        try:
            op.drop_index(idx, table_name="incidencia")
        except Exception:
            pass
    # recrea índices simples antiguos si quieres fidelidad 100%
    try:
        op.create_index(op.f("ix_incidencia_fecha"), "incidencia", ["fecha"], unique=False)
    except Exception:
        pass
    try:
        op.create_index(op.f("ix_incidencia_estado"), "incidencia", ["estado"], unique=False)
    except Exception:
        pass
    try:
        op.create_index(op.f("ix_incidencia_equipo_id"), "incidencia", ["equipo_id"], unique=False)
    except Exception:
        pass

    for fk in ("inc_usuario_modificador_fk", "inc_cerrada_por_fk", "inc_usuario_fk"):
        try:
            op.drop_constraint(fk, "incidencia", type_="foreignkey")
        except Exception:
            pass

    try:
        op.alter_column(
            "incidencia",
            "descripcion",
            existing_type=sa.Text(),
            type_=sa.VARCHAR(length=2000),
            existing_nullable=True,
        )
    except Exception:
        pass
    try:
        op.alter_column(
            "incidencia",
            "fecha",
            existing_type=sa.DateTime(timezone=True),
            server_default=None,
            type_=postgresql.TIMESTAMP(),
            nullable=False,
        )
    except Exception:
        pass
    for col in ("usuario_modificador_id", "usuario_id", "cerrada_por_id", "cerrada_en", "actualizada_en"):
        try:
            op.drop_column("incidencia", col)
        except Exception:
            pass

    # EQUIPO
    for idx in ("ix_equipo_tipo", "ix_equipo_estado_tipo", "ix_equipo_estado"):
        try:
            op.drop_index(idx, table_name="equipo")
        except Exception:
            pass

    try:
        op.alter_column(
            "equipo",
            "numero_serie",
            existing_type=sa.String(length=150),
            type_=sa.VARCHAR(length=128),
            existing_nullable=True,
        )
    except Exception:
        pass
    try:
        op.alter_column(
            "equipo",
            "identidad",
            existing_type=sa.String(length=100),
            type_=sa.VARCHAR(length=64),
            nullable=False,
        )
    except Exception:
        pass

    for col in ("actualizado_en", "creado_en", "estado", "tipo"):
        try:
            op.drop_column("equipo", col)
        except Exception:
            pass

    # En algunos esquemas antiguos existían unique simples:
    try:
        op.create_unique_constraint(op.f("uq_equipo_nfc_tag"), "equipo", ["nfc_tag"])
    except Exception:
        pass
    try:
        op.create_unique_constraint(op.f("uq_equipo_identidad"), "equipo", ["identidad"])
    except Exception:
        pass
