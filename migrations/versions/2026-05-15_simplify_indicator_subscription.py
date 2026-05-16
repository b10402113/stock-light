"""simplify indicator subscription to always use condition_group

Revision ID: simplify_indicator_subscription
Revises: stock_indicator_table
Create Date: 2026-05-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'simplify_indicator_subscription'
down_revision: Union[str, None] = 'stock_indicator_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Migrate existing single-condition subscriptions to condition_group format
    # Use raw SQL for data migration
    op.execute("""
        UPDATE indicator_subscriptions
        SET compound_condition = jsonb_build_object(
            'logic', 'and',
            'conditions', jsonb_build_array(
                jsonb_build_object(
                    'indicator_type', indicator_type,
                    'operator', operator,
                    'target_value', target_value,
                    'timeframe', timeframe,
                    'period', period
                )
            )
        )
        WHERE compound_condition IS NULL
          AND indicator_type IS NOT NULL
          AND operator IS NOT NULL
          AND target_value IS NOT NULL
    """)

    # 2. Drop the unique index for single conditions
    op.drop_index(
        'uix_user_stock_single_condition',
        table_name='indicator_subscriptions',
        postgresql_where='(is_deleted = false AND compound_condition IS NULL)'
    )

    # 3. Drop CHECK constraints that will no longer apply
    op.drop_constraint('chk_period_range', 'indicator_subscriptions', type_='check')
    op.drop_constraint('chk_timeframe_valid', 'indicator_subscriptions', type_='check')

    # 4. Remove nullable columns (indicator_type, operator, target_value)
    op.drop_column('indicator_subscriptions', 'indicator_type')
    op.drop_column('indicator_subscriptions', 'operator')
    op.drop_column('indicator_subscriptions', 'target_value')

    # 5. Remove timeframe and period columns (now inside each condition)
    op.drop_column('indicator_subscriptions', 'period')
    op.drop_column('indicator_subscriptions', 'timeframe')

    # 6. Make compound_condition NOT NULL
    op.alter_column(
        'indicator_subscriptions',
        'compound_condition',
        existing_type=postgresql.JSONB(astext_type=sa.Text()),
        nullable=False
    )

    # 7. Rename column: compound_condition -> condition_group
    op.alter_column(
        'indicator_subscriptions',
        'compound_condition',
        new_column_name='condition_group'
    )

    # 8. Add CHECK constraint to validate condition_group structure
    op.create_check_constraint(
        'chk_condition_group_structure',
        'indicator_subscriptions',
        """
        condition_group ? 'logic' AND
        condition_group ? 'conditions' AND
        condition_group->>'logic' IN ('and', 'or') AND
        jsonb_array_length(condition_group->'conditions') >= 1 AND
        jsonb_array_length(condition_group->'conditions') <= 10
        """
    )

    # 9. Create new unique index on (user_id, stock_id, condition_group)
    op.create_index(
        'uix_user_stock_condition_group',
        'indicator_subscriptions',
        ['user_id', 'stock_id', 'condition_group'],
        unique=True,
        postgresql_where='(is_deleted = false)'
    )


def downgrade() -> None:
    # 1. Drop new unique index
    op.drop_index(
        'uix_user_stock_condition_group',
        table_name='indicator_subscriptions',
        postgresql_where='(is_deleted = false)'
    )

    # 2. Drop CHECK constraint
    op.drop_constraint('chk_condition_group_structure', 'indicator_subscriptions', type_='check')

    # 3. Rename column back: condition_group -> compound_condition
    op.alter_column(
        'indicator_subscriptions',
        'condition_group',
        new_column_name='compound_condition'
    )

    # 4. Make compound_condition nullable again
    op.alter_column(
        'indicator_subscriptions',
        'compound_condition',
        existing_type=postgresql.JSONB(astext_type=sa.Text()),
        nullable=True
    )

    # 5. Re-add timeframe column
    op.add_column(
        'indicator_subscriptions',
        sa.Column('timeframe', sa.String(length=1), nullable=False, server_default='D')
    )

    # 6. Re-add period column
    op.add_column(
        'indicator_subscriptions',
        sa.Column('period', sa.SmallInteger(), nullable=True)
    )

    # 7. Re-add CHECK constraints
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

    # 8. Re-add nullable columns (indicator_type, operator, target_value)
    op.add_column(
        'indicator_subscriptions',
        sa.Column('indicator_type', sa.String(length=50), nullable=True)
    )
    op.add_column(
        'indicator_subscriptions',
        sa.Column('operator', sa.String(length=10), nullable=True)
    )
    op.add_column(
        'indicator_subscriptions',
        sa.Column('target_value', sa.Numeric(precision=10, scale=4), nullable=True)
    )

    # 9. Revert data migration: extract single condition from compound_condition
    # Note: This only works for subscriptions with exactly 1 condition
    op.execute("""
        UPDATE indicator_subscriptions
        SET
            indicator_type = compound_condition->'conditions'->0->>'indicator_type',
            operator = compound_condition->'conditions'->0->>'operator',
            target_value = (compound_condition->'conditions'->0->>'target_value')::numeric,
            timeframe = compound_condition->'conditions'->0->>'timeframe',
            period = (compound_condition->'conditions'->0->>'period')::smallint,
            compound_condition = NULL
        WHERE jsonb_array_length(compound_condition->'conditions') = 1
          AND compound_condition->>'logic' = 'and'
    """)

    # 10. Recreate old unique index
    op.create_index(
        'uix_user_stock_single_condition',
        'indicator_subscriptions',
        ['user_id', 'stock_id', 'indicator_type', 'operator', 'target_value', 'timeframe', 'period'],
        unique=True,
        postgresql_where='(is_deleted = false AND compound_condition IS NULL)'
    )