"""citext + ondelete set null

Revision ID: d38a1a881416
Revises: 56034520f738
Create Date: 2025-10-25 21:30:54.091687
"""

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision = 'd38a1a881416'
down_revision = '56034520f738'
branch_labels = None
depends_on = None

def upgrade():
    # 1) Extensión CITEXT (idempotente)
    op.execute("CREATE EXTENSION IF NOT EXISTS citext;")

    # 2) Cambiar seccion.nombre -> CITEXT conservando datos
    #    Tu columna actual es VARCHAR(100).
    with op.batch_alter_table("seccion") as batch_op:
        batch_op.alter_column(
            "nombre",
            type_=sa.dialects.postgresql.CITEXT(),
            existing_type=sa.String(length=100),
            existing_nullable=False,
            postgresql_using="nombre::citext",
        )

    # 3) Re-crear FKs con ON DELETE SET NULL

    # UBICACION.seccion_id
    op.drop_constraint("ubicacion_seccion_id_fkey", "ubicacion", type_="foreignkey")
    op.create_foreign_key(
        "ubicacion_seccion_id_fkey",
        source_table="ubicacion",
        referent_table="seccion",
        local_cols=["seccion_id"],
        remote_cols=["id"],
        ondelete="SET NULL",
    )

    # EQUIPO.seccion_id
    op.drop_constraint("equipo_seccion_id_fkey", "equipo", type_="foreignkey")
    op.create_foreign_key(
        "equipo_seccion_id_fkey",
        source_table="equipo",
        referent_table="seccion",
        local_cols=["seccion_id"],
        remote_cols=["id"],
        ondelete="SET NULL",
    )


def downgrade():
    # Revertir FKs a sin ondelete
    op.drop_constraint("equipo_seccion_id_fkey", "equipo", type_="foreignkey")
    op.create_foreign_key(
        "equipo_seccion_id_fkey",
        source_table="equipo",
        referent_table="seccion",
        local_cols=["seccion_id"],
        remote_cols=["id"],
    )

    op.drop_constraint("ubicacion_seccion_id_fkey", "ubicacion", type_="foreignkey")
    op.create_foreign_key(
        "ubicacion_seccion_id_fkey",
        source_table="ubicacion",
        referent_table="seccion",
        local_cols=["seccion_id"],
        remote_cols=["id"],
    )

    # Volver seccion.nombre a VARCHAR(100)
    with op.batch_alter_table("seccion") as batch_op:
        batch_op.alter_column(
            "nombre",
            type_=sa.String(length=100),
            existing_type=sa.dialects.postgresql.CITEXT(),
            existing_nullable=False,
            postgresql_using="nombre::text",
        )

    # (Opcional) Borrar extensión
    # op.execute("DROP EXTENSION IF EXISTS citext;")