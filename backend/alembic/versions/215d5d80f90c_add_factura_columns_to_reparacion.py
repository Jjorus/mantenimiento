"""add factura columns to reparacion

Revision ID: 215d5d80f90c
Revises: a4c329b7059c
Create Date: 2025-11-23 04:11:59.645753
"""

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision = '215d5d80f90c'
down_revision = 'a4c329b7059c'
branch_labels = None
depends_on = None

def upgrade():
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


def downgrade():
    op.drop_column("reparacion", "factura_tamano_bytes")
    op.drop_column("reparacion", "factura_content_type")
    op.drop_column("reparacion", "factura_archivo_path")
    op.drop_column("reparacion", "factura_archivo_nombre")