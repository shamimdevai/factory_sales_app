"""Add customer_types, customer_tiers, app_settings tables and customers.customer_type_id

Revision ID: a1b2c3d4e5f6
Revises: f7c3d81a2e56
Create Date: 2026-08-08 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'f7c3d81a2e56'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # customer_types
    op.create_table(
        'customer_types',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )
    op.create_index(op.f('ix_customer_types_id'), 'customer_types', ['id'], unique=False)

    # customer_tiers (UI label: "Status" — see models.py note)
    op.create_table(
        'customer_tiers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('min_amount', sa.Float(), nullable=False),
        sa.Column('period', sa.String(length=10), nullable=False, server_default='monthly'),
        sa.Column('rank', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('rank'),
    )
    op.create_index(op.f('ix_customer_tiers_id'), 'customer_tiers', ['id'], unique=False)

    # app_settings (singleton row, id=1)
    op.create_table(
        'app_settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('grace_days', sa.Integer(), nullable=False, server_default='30'),
        sa.Column('decay_step_days', sa.Integer(), nullable=False, server_default='30'),
        sa.PrimaryKeyConstraint('id'),
    )
    # seed the single settings row so the app never has to special-case "no row yet"
    op.execute("INSERT INTO app_settings (id, grace_days, decay_step_days) VALUES (1, 30, 30)")

    # customers.customer_type_id
    op.add_column(
        'customers',
        sa.Column('customer_type_id', sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        'fk_customers_customer_type_id',
        'customers', 'customer_types',
        ['customer_type_id'], ['id'],
        ondelete='SET NULL'
    )

    # --- Seed default Customer Types (admin can add/edit/delete later) ---
    op.execute(
        "INSERT INTO customer_types (name) VALUES "
        "('Retail'), ('Wholesale'), ('Distributor'), ('Farmer')"
    )

    # --- Seed default Status tiers (placeholder thresholds — admin should
    # revisit these for their actual business, editable later) ---
    op.execute(
        "INSERT INTO customer_tiers (name, min_amount, period, rank) VALUES "
        "('Silver', 10000, 'monthly', 1), "
        "('Golden', 50000, 'monthly', 2), "
        "('Platinum', 100000, 'monthly', 3)"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('fk_customers_customer_type_id', 'customers', type_='foreignkey')
    op.drop_column('customers', 'customer_type_id')

    op.drop_table('app_settings')

    op.drop_index(op.f('ix_customer_tiers_id'), table_name='customer_tiers')
    op.drop_table('customer_tiers')

    op.drop_index(op.f('ix_customer_types_id'), table_name='customer_types')
    op.drop_table('customer_types')