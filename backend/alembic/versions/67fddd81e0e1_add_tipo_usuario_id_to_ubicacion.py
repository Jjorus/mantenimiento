"""Add tipo & usuario_id to ubicacion

Revision ID: 67fddd81e0e1
Revises: 728b57b94611
Create Date: 2025-11-23 00:03:23.572709
"""

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision = '67fddd81e0e1'
down_revision = '728b57b94611'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # 1) Columna tipo con default 'OTRO' y NOT NULL
    op.add_column(
        "ubicacion",
        sa.Column("tipo", sa.String(length=20), nullable=False, server_default="OTRO"),
    )

    # 2) Columna usuario_id nullable, única, con FK a usuario.id
    op.add_column(
        "ubicacion",
        sa.Column("usuario_id", sa.Integer(), nullable=True),
    )
    op.create_unique_constraint(
        "uq_ubicacion_usuario_id", "ubicacion", ["usuario_id"]
    )
    op.create_foreign_key(
        "fk_ubicacion_usuario",
        "ubicacion",
        "usuario",
        ["usuario_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # 3) Check constraint para tipo
    op.create_check_constraint(
        "ck_ubicacion_tipo",
        "ubicacion",
        "tipo in ('ALMACEN','LABORATORIO','TECNICO','OTRO')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_ubicacion_tipo", "ubicacion", type_="check")
    op.drop_constraint("fk_ubicacion_usuario", "ubicacion", type_="foreignkey")
    op.drop_constraint("uq_ubicacion_usuario_id", "ubicacion", type_="unique")
    op.drop_column("ubicacion", "usuario_id")
    op.drop_column("ubicacion", "tipo")