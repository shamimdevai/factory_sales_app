"""Add invoice_date (business date) column

Revision ID: j6k7l8m9n0o1
Revises: i5j6k7l8m9n0
Create Date: 2026-08-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'j6k7l8m9n0o1'
down_revision: Union[str, Sequence[str], None] = 'i5j6k7l8m9n0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Nullable at first so we can backfill existing rows before locking it down.
    op.add_column('invoices', sa.Column('invoice_date', sa.Date(), nullable=True))
    op.create_index(op.f('ix_invoices_invoice_date'), 'invoices', ['invoice_date'], unique=False)

    # Backfill: invoice_date = local calendar date of created_at, matching the
    # app's UTC+6 storage convention (see src/utils/time_utils.py).
    op.execute("UPDATE invoices SET invoice_date = (created_at + INTERVAL '6 hours')::date")

    op.alter_column('invoices', 'invoice_date', nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_invoices_invoice_date'), table_name='invoices')
    op.drop_column('invoices', 'invoice_date')