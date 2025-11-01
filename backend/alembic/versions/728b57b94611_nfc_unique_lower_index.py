"""nfc: unique lower index

Revision ID: 728b57b94611
Revises: b3393d72c463
Create Date: 2025-11-01 22:17:37.946073
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "728b57b94611"
down_revision = "b3393d72c463"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Limpieza defensiva (NO tocamos ix_equipo_nfc_tag)
    op.execute('DROP INDEX IF EXISTS public.ix_equipo_nfc_tag_lower_unique;')
    op.execute('ALTER TABLE public.equipo DROP CONSTRAINT IF EXISTS uq_equipo_nfc_tag;')

    # Índice único funcional case-insensitive (permite múltiples NULL)
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS public.ix_equipo_nfc_tag_lower_unique
        ON public.equipo (LOWER(nfc_tag))
        WHERE nfc_tag IS NOT NULL;
        """
    )


def downgrade() -> None:
    # Solo quitamos el índice funcional; dejamos ix_equipo_nfc_tag tal cual
    op.execute('DROP INDEX IF EXISTS public.ix_equipo_nfc_tag_lower_unique;')

    # (Opcional) si quieres restaurar un UNIQUE plano anterior, descomenta:
    # op.execute('ALTER TABLE equipo ADD CONSTRAINT uq_equipo_nfc_tag UNIQUE (nfc_tag);')
