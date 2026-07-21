"""Add due-payment chain support (parent_invoice_id, is_due_payment)

Revision ID: e2a9c1f74d38
Revises: d7f3a2c8b915
Create Date: 2026-07-20 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e2a9c1f74d38'
down_revision: Union[str, Sequence[str], None] = 'd7f3a2c8b915'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('invoices', sa.Column('parent_invoice_id', sa.Integer(), nullable=True))
    op.add_column(
        'invoices',
        sa.Column('is_due_payment', sa.Boolean(), nullable=False, server_default=sa.false())
    )
    op.create_foreign_key(
        'fk_invoices_parent_invoice_id',
        'invoices', 'invoices',
        ['parent_invoice_id'], ['id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('fk_invoices_parent_invoice_id', 'invoices', type_='foreignkey')
    op.drop_column('invoices', 'is_due_payment')
    op.drop_column('invoices', 'parent_invoice_id')