"""fix compound condition model nullable and indexes

Revision ID: fix_compound_condition_model
Revises: scheduled_reminders_table
Create Date: 2026-05-10

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fix_compound_condition_model'
down_revision: Union[str, None] = 'scheduled_reminders_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Change nullable constraints for single condition fields (NOT NULL -> NULL)
    op.alter_column(
        'indicator_subscriptions',
        'indicator_type',
        existing_type=sa.String(length=50),
        nullable=True
    )
    op.alter_column(
        'indicator_subscriptions',
        'operator',
        existing_type=sa.String(length=10),
        nullable=True
    )
    op.alter_column(
        'indicator_subscriptions',
        'target_value',
        existing_type=sa.Numeric(precision=10, scale=4),
        nullable=True
    )

    # 2. Drop redundant indexes
    op.drop_index('indicator_subscriptions_is_active_idx', table_name='indicator_subscriptions')
    op.drop_index('indicator_subscriptions_user_id_idx', table_name='indicator_subscriptions')
    op.drop_index('indicator_subscriptions_stock_id_idx', table_name='indicator_subscriptions')
    op.drop_index('indicator_subscriptions_user_stock_idx', table_name='indicator_subscriptions')
    op.drop_index('indicator_subscriptions_user_indicator_key', table_name='indicator_subscriptions')

    # 3. Create optimized partial indexes
    # Index for price trigger queries (stock_id + is_active + is_deleted)
    op.create_index(
        'idx_indicator_subs_on_stock_active',
        'indicator_subscriptions',
        ['stock_id'],
        postgresql_where='(is_active = true AND is_deleted = false)'
    )

    # Index for user list queries (user_id + is_deleted)
    op.create_index(
        'idx_indicator_subs_on_user',
        'indicator_subscriptions',
        ['user_id'],
        postgresql_where='(is_deleted = false)'
    )

    # Unique constraint only for single conditions (compound_condition IS NULL)
    op.create_index(
        'uix_user_stock_single_condition',
        'indicator_subscriptions',
        ['user_id', 'stock_id', 'indicator_type', 'operator', 'target_value'],
        unique=True,
        postgresql_where='(is_deleted = false AND compound_condition IS NULL)'
    )


def downgrade() -> None:
    # 1. Drop new indexes
    op.drop_index('uix_user_stock_single_condition', table_name='indicator_subscriptions', postgresql_where='(is_deleted = false AND compound_condition IS NULL)')
    op.drop_index('idx_indicator_subs_on_user', table_name='indicator_subscriptions', postgresql_where='(is_deleted = false)')
    op.drop_index('idx_indicator_subs_on_stock_active', table_name='indicator_subscriptions', postgresql_where='(is_active = true AND is_deleted = false)')

    # 2. Recreate old indexes
    op.create_index(
        'indicator_subscriptions_user_indicator_key',
        'indicator_subscriptions',
        ['user_id', 'stock_id', 'indicator_type', 'operator', 'target_value'],
        unique=True,
        postgresql_where='is_deleted = false'
    )
    op.create_index('indicator_subscriptions_user_stock_idx', 'indicator_subscriptions', ['user_id', 'stock_id'])
    op.create_index('indicator_subscriptions_stock_id_idx', 'indicator_subscriptions', ['stock_id'])
    op.create_index('indicator_subscriptions_user_id_idx', 'indicator_subscriptions', ['user_id'])
    op.create_index('indicator_subscriptions_is_active_idx', 'indicator_subscriptions', ['is_active'])

    # 3. Restore NOT NULL constraints (NULL -> NOT NULL)
    # Note: This will fail if there are NULL values in the database
    op.alter_column(
        'indicator_subscriptions',
        'target_value',
        existing_type=sa.Numeric(precision=10, scale=4),
        nullable=False
    )
    op.alter_column(
        'indicator_subscriptions',
        'operator',
        existing_type=sa.String(length=10),
        nullable=False
    )
    op.alter_column(
        'indicator_subscriptions',
        'indicator_type',
        existing_type=sa.String(length=50),
        nullable=False
    )