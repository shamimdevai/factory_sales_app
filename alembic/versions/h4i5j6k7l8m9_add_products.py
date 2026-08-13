"""Add products table

Revision ID: h4i5j6k7l8m9
Revises: g2h3i4j5k6l7
Create Date: 2026-08-11 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'h4i5j6k7l8m9'
down_revision: Union[str, Sequence[str], None] = 'g2h3i4j5k6l7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'products',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('unit', sa.String(length=20), nullable=False, server_default='kg'),
        sa.Column('default_price', sa.Float(), nullable=False, server_default='0'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )
    op.create_index(op.f('ix_products_id'), 'products', ['id'], unique=False)

    # --- Seed with the 4 products that used to be hardcoded in the Invoice
    # Terminal's dropdown, so nothing disappears from the picker on upgrade.
    # All admin-editable afterward via Settings -> Products.
    op.execute(
        "INSERT INTO products (name, unit, default_price) VALUES "
        "('Premium Vermi-Compost', 'kg', 25.0), "
        "('Organic Earthworm Castings', 'kg', 25.0), "
        "('Compost Starter Culture', 'kg', 25.0), "
        "('Liquid Bio-Fertilizer', 'kg', 25.0)"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_products_id'), table_name='products')
    op.drop_table('products')