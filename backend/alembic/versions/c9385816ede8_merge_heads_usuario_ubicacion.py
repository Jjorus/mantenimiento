"""merge heads: usuario + ubicacion

Revision ID: c9385816ede8
Revises: adc6fbc7ed40, e3f1a2b9c7d0
Create Date: 2025-11-01 19:57:53.093381
"""

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision = 'c9385816ede8'
down_revision = ('adc6fbc7ed40', 'e3f1a2b9c7d0')
branch_labels = None
depends_on = None

def upgrade() -> None:
    pass

def downgrade() -> None:
    pass