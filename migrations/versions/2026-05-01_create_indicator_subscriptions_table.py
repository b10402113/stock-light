"""create indicator_subscriptions table

Revision ID: indicator_subscriptions
Revises: watchlists_tables
Create Date: 2026-05-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'indicator_subscriptions'
down_revision: Union[str, None] = 'watchlists_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create indicator_subscriptions table
    op.create_table(
        'indicator_subscriptions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('stock_id', sa.Integer(), sa.ForeignKey('stocks.id'), nullable=False),
        sa.Column('indicator_type', sa.String(length=50), nullable=False),
        sa.Column('operator', sa.String(length=10), nullable=False),
        sa.Column('target_value', sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column('compound_condition', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('is_triggered', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('cooldown_end_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.PrimaryKeyConstraint('id'),
    )

    # Create indexes for indicator_subscriptions
    op.create_index('indicator_subscriptions_user_id_idx', 'indicator_subscriptions', ['user_id'], unique=False)
    op.create_index('indicator_subscriptions_stock_id_idx', 'indicator_subscriptions', ['stock_id'], unique=False)
    op.create_index('indicator_subscriptions_is_active_idx', 'indicator_subscriptions', ['is_active'], unique=False)
    op.create_index('indicator_subscriptions_user_stock_idx', 'indicator_subscriptions', ['user_id', 'stock_id'], unique=False)
    # Create unique partial index for duplicate prevention
    op.execute(
        "CREATE UNIQUE INDEX indicator_subscriptions_user_indicator_key ON indicator_subscriptions "
        "(user_id, stock_id, indicator_type, operator, target_value) "
        "WHERE is_deleted = false"
    )


def downgrade() -> None:
    # Drop indicator_subscriptions table
    op.execute("DROP INDEX IF EXISTS indicator_subscriptions_user_indicator_key")
    op.drop_index('indicator_subscriptions_user_stock_idx', table_name='indicator_subscriptions')
    op.drop_index('indicator_subscriptions_is_active_idx', table_name='indicator_subscriptions')
    op.drop_index('indicator_subscriptions_stock_id_idx', table_name='indicator_subscriptions')
    op.drop_index('indicator_subscriptions_user_id_idx', table_name='indicator_subscriptions')
    op.drop_table('indicator_subscriptions')
