"""Add less_adjustment to invoices

Revision ID: d7f3a2c8b915
Revises: c4d8f2a91b6e
Create Date: 2026-07-18 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd7f3a2c8b915'
down_revision: Union[str, Sequence[str], None] = 'c4d8f2a91b6e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('invoices', sa.Column('less_adjustment', sa.Float(), nullable=False, server_default='0'))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('invoices', 'less_adjustment')