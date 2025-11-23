"""add incidencia and billing fields to reparacion

Revision ID: 47a5ca083aba
Revises: 67fddd81e0e1
Create Date: 2025-11-23 01:26:48.448230
"""

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision = '47a5ca083aba'
down_revision = '67fddd81e0e1'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Nuevas columnas
    op.add_column(
        "reparacion",
        sa.Column("incidencia_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "reparacion",
        sa.Column("coste_materiales", sa.Numeric(10, 2), nullable=True),
    )
    op.add_column(
        "reparacion",
        sa.Column("coste_mano_obra", sa.Numeric(10, 2), nullable=True),
    )
    op.add_column(
        "reparacion",
        sa.Column("coste_otros", sa.Numeric(10, 2), nullable=True),
    )
    op.add_column(
        "reparacion",
        sa.Column("moneda", sa.String(length=3), nullable=True, server_default="EUR"),
    )
    op.add_column(
        "reparacion",
        sa.Column("proveedor", sa.String(length=150), nullable=True),
    )
    op.add_column(
        "reparacion",
        sa.Column("numero_factura", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "reparacion",
        sa.Column("factura_archivo_nombre", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "reparacion",
        sa.Column("factura_archivo_path", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "reparacion",
        sa.Column("factura_content_type", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "reparacion",
        sa.Column("factura_tamano_bytes", sa.Integer(), nullable=True),
    )

    # FK + índices
    op.create_foreign_key(
        "fk_reparacion_incidencia",
        "reparacion",
        "incidencia",
        ["incidencia_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_reparacion_incidencia",
        "reparacion",
        ["incidencia_id"],
        unique=False,
    )
    op.create_unique_constraint(
        "uq_reparacion_equipo_incidencia",
        "reparacion",
        ["equipo_id", "incidencia_id"],
    )

    # Si NO tienes datos previos en reparacion, puedes forzar NOT NULL:
    #op.alter_column("reparacion", "incidencia_id", nullable=False)


def downgrade() -> None:
    op.drop_constraint("uq_reparacion_equipo_incidencia", "reparacion", type_="unique")
    op.drop_constraint("fk_reparacion_incidencia", "reparacion", type_="foreignkey")
    op.drop_index("ix_reparacion_incidencia", table_name="reparacion")

    op.drop_column("reparacion", "factura_tamano_bytes")
    op.drop_column("reparacion", "factura_content_type")
    op.drop_column("reparacion", "factura_archivo_path")
    op.drop_column("reparacion", "factura_archivo_nombre")
    op.drop_column("reparacion", "numero_factura")
    op.drop_column("reparacion", "proveedor")
    op.drop_column("reparacion", "moneda")
    op.drop_column("reparacion", "coste_otros")
    op.drop_column("reparacion", "coste_mano_obra")
    op.drop_column("reparacion", "coste_materiales")
    op.drop_column("reparacion", "incidencia_id")