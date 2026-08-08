"""Add rank_hold_months to app_settings

Revision ID: g2h3i4j5k6l7
Revises: a1b2c3d4e5f6
Create Date: 2026-08-08 01:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'g2h3i4j5k6l7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'app_settings',
        sa.Column('rank_hold_months', sa.Integer(), nullable=False, server_default='6')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('app_settings', 'rank_hold_months')