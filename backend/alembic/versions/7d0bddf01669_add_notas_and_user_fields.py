"""add_notas_and_user_fields

Revision ID: 7d0bddf01669
Revises: 886e039c7746
Create Date: 2025-11-27 09:28:33.412396
"""

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision = "7d0bddf01669"
down_revision = "886e039c7746"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Añadir columna "notas" a la tabla usuario
    op.add_column("usuario", sa.Column("notas", sa.Text(), nullable=True))

    # Crear tabla de adjuntos de usuario
    op.create_table(
        "usuario_adjunto",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("nombre_archivo", sa.String(length=255), nullable=False),
        sa.Column("ruta_relativa", sa.String(length=500), nullable=False),
        sa.Column(
            "content_type",
            sqlmodel.sql.sqltypes.AutoString(length=100),
            nullable=True,
        ),
        sa.Column("tamano_bytes", sa.Integer(), nullable=True),
        sa.Column(
            "subido_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("subido_por_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["usuario_id"], ["usuario.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["subido_por_id"], ["usuario.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    # El orden inverso al upgrade
    op.drop_table("usuario_adjunto")
    op.drop_column("usuario", "notas")
