"""add timeframe and period fields to indicator_subscriptions

Revision ID: timeframe_period_fields
Revises: fix_compound_condition_model
Create Date: 2026-05-14

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'timeframe_period_fields'
down_revision: Union[str, None] = 'daily_prices_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add timeframe column (VARCHAR(1), NOT NULL, DEFAULT 'D')
    op.add_column(
        'indicator_subscriptions',
        sa.Column('timeframe', sa.String(length=1), nullable=False, server_default='D')
    )

    # 2. Add period column (SMALLINT, NULL)
    op.add_column(
        'indicator_subscriptions',
        sa.Column('period', sa.SmallInteger(), nullable=True)
    )

    # 3. Add CHECK constraints
    op.create_check_constraint(
        'chk_timeframe_valid',
        'indicator_subscriptions',
        "timeframe IN ('D', 'W')"
    )
    op.create_check_constraint(
        'chk_period_range',
        'indicator_subscriptions',
        "(period >= 5 AND period <= 200) OR period IS NULL"
    )

    # 4. Drop old unique index
    op.drop_index(
        'uix_user_stock_single_condition',
        table_name='indicator_subscriptions',
        postgresql_where='(is_deleted = false AND compound_condition IS NULL)'
    )

    # 5. Create new unique index with timeframe and period included
    op.create_index(
        'uix_user_stock_single_condition',
        'indicator_subscriptions',
        ['user_id', 'stock_id', 'indicator_type', 'operator', 'target_value', 'timeframe', 'period'],
        unique=True,
        postgresql_where='(is_deleted = false AND compound_condition IS NULL)'
    )


def downgrade() -> None:
    # 1. Drop new unique index
    op.drop_index(
        'uix_user_stock_single_condition',
        table_name='indicator_subscriptions',
        postgresql_where='(is_deleted = false AND compound_condition IS NULL)'
    )

    # 2. Recreate old unique index (without timeframe and period)
    op.create_index(
        'uix_user_stock_single_condition',
        'indicator_subscriptions',
        ['user_id', 'stock_id', 'indicator_type', 'operator', 'target_value'],
        unique=True,
        postgresql_where='(is_deleted = false AND compound_condition IS NULL)'
    )

    # 3. Drop CHECK constraints
    op.drop_check_constraint('chk_period_range', 'indicator_subscriptions')
    op.drop_check_constraint('chk_timeframe_valid', 'indicator_subscriptions')

    # 4. Drop columns
    op.drop_column('indicator_subscriptions', 'period')
    op.drop_column('indicator_subscriptions', 'timeframe')