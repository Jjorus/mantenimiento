"""add reparacion_factura table

Revision ID: a4c329b7059c
Revises: 47a5ca083aba
Create Date: 2025-11-23 03:29:18.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a4c329b7059c"
down_revision = "47a5ca083aba"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ---- Nueva tabla de facturas por reparación ----
    op.create_table(
        "reparacion_factura",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column(
            "reparacion_id",
            sa.Integer(),
            sa.ForeignKey("reparacion.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("nombre_original", sa.String(length=255), nullable=True),
        sa.Column("path_relativo", sa.String(length=500), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=True),
        sa.Column("tamano_bytes", sa.Integer(), nullable=False),
        sa.Column(
            "subido_en",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "subido_por_id",
            sa.Integer(),
            sa.ForeignKey("usuario.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    op.create_index(
        "ix_reparacion_factura_reparacion_id",
        "reparacion_factura",
        ["reparacion_id"],
    )

    # ---- Limpiar columnas antiguas de factura en reparacion ----
    # Ojo: aquí NO tocamos incidencia_id para evitar el error de NOT NULL
    with op.batch_alter_table("reparacion", schema=None) as batch_op:
        # Si ya no quieres las columnas antiguas en la tabla reparacion
        batch_op.drop_column("factura_archivo_nombre")
        batch_op.drop_column("factura_archivo_path")
        batch_op.drop_column("factura_content_type")
        batch_op.drop_column("factura_tamano_bytes")


def downgrade() -> None:
    # Restaurar columnas antiguas si se hace downgrade
    with op.batch_alter_table("reparacion", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("factura_tamano_bytes", sa.Integer(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("factura_content_type", sa.String(length=100), nullable=True)
        )
        batch_op.add_column(
            sa.Column("factura_archivo_path", sa.String(length=500), nullable=True)
        )
        batch_op.add_column(
            sa.Column("factura_archivo_nombre", sa.String(length=255), nullable=True)
        )

    op.drop_index("ix_reparacion_factura_reparacion_id", table_name="reparacion_factura")
    op.drop_table("reparacion_factura")
