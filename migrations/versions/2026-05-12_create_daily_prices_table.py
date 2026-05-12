"""create daily_prices table

Revision ID: daily_prices_table
Revises: fix_compound_condition_model
Create Date: 2026-05-12

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'daily_prices_table'
down_revision: Union[str, None] = 'fix_compound_condition_model'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create daily_prices table
    op.create_table(
        'daily_prices',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('stock_id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('open', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('high', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('low', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('close', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('volume', sa.BigInteger(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['stock_id'], ['stocks.id'], ondelete='CASCADE'),
    )

    # Create unique constraint on (stock_id, date)
    op.create_unique_constraint('uq_daily_price_stock_date', 'daily_prices', ['stock_id', 'date'])

    # Create composite index on (stock_id, date) for range queries
    op.create_index('idx_daily_price_stock_date', 'daily_prices', ['stock_id', 'date'], unique=False)


def downgrade() -> None:
    # Drop index
    op.drop_index('idx_daily_price_stock_date', table_name='daily_prices')

    # Drop unique constraint
    op.drop_constraint('uq_daily_price_stock_date', 'daily_prices', type_='unique')

    # Drop table
    op.drop_table('daily_prices')