"""Add transport_charge and show_transport_charge to invoices

Revision ID: f7c3d81a2e56
Revises: e2a9c1f74d38
Create Date: 2026-07-25 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f7c3d81a2e56'
down_revision: Union[str, Sequence[str], None] = 'e2a9c1f74d38'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('invoices', sa.Column('transport_charge', sa.Float(), nullable=False, server_default='0'))
    op.add_column(
        'invoices',
        sa.Column('show_transport_charge', sa.Boolean(), nullable=False, server_default=sa.false())
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('invoices', 'show_transport_charge')
    op.drop_column('invoices', 'transport_charge')