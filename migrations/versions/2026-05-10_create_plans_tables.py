"""create level_configs and plans tables

Revision ID: plans_tables
Revises: stock_source_market
Create Date: 2026-05-10

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = 'plans_tables'
down_revision: Union[str, None] = 'stock_source_market'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create level_configs table
    op.create_table(
        'level_configs',
        sa.Column('level', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('monthly_price', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('yearly_price', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('max_subscriptions', sa.Integer(), nullable=False),
        sa.Column('max_alerts', sa.Integer(), nullable=False),
        sa.Column('features', JSONB, nullable=True),
        sa.Column('is_purchasable', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.PrimaryKeyConstraint('level'),
    )

    # Seed default level configs
    op.execute("""
        INSERT INTO level_configs (level, name, monthly_price, yearly_price, max_subscriptions, max_alerts, features, is_purchasable, is_deleted)
        VALUES
            (1, 'Regular', 0.00, 0.00, 10, 10, NULL, false, false),
            (2, 'Pro', 99.00, 999.00, 50, 50, NULL, true, false),
            (3, 'Pro Max', 199.00, 1999.00, 100, 100, NULL, true, false),
            (4, 'Admin', 0.00, 0.00, -1, -1, NULL, false, false)
    """)

    # Create plans table
    op.create_table(
        'plans',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('level', sa.Integer(), nullable=False),
        sa.Column('billing_cycle', sa.String(length=10), nullable=False),
        sa.Column('price', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('due_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
    )

    # Create indexes
    op.create_index('plans_user_id_idx', 'plans', ['user_id'])
    op.create_index('plans_user_active_idx', 'plans', ['user_id', 'is_active'])

    # Seed existing users with Level 1 Plan (permanent)
    op.execute("""
        INSERT INTO plans (user_id, level, billing_cycle, price, due_date, is_active, is_deleted)
        SELECT id, 1, 'yearly', 0.00, '9999-12-31 23:59:59', true, false
        FROM users
        WHERE is_deleted = false
    """)


def downgrade() -> None:
    # Drop indexes
    op.drop_index('plans_user_active_idx', table_name='plans')
    op.drop_index('plans_user_id_idx', table_name='plans')

    # Drop tables
    op.drop_table('plans')
    op.drop_table('level_configs')