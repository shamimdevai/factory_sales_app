"""Add discount_amount and paid_amount to invoices

Revision ID: c4d8f2a91b6e
Revises: 8f6a5632b5e4
Create Date: 2026-07-16 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c4d8f2a91b6e'
down_revision: Union[str, Sequence[str], None] = '8f6a5632b5e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('invoices', sa.Column('discount_amount', sa.Float(), nullable=False, server_default='0'))
    op.add_column('invoices', sa.Column('paid_amount', sa.Float(), nullable=False, server_default='0'))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('invoices', 'paid_amount')
    op.drop_column('invoices', 'discount_amount')