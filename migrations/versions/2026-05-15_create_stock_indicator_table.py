"""create stock_indicator table

Revision ID: stock_indicator_table
Revises: timeframe_period_fields
Create Date: 2026-05-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'stock_indicator_table'
down_revision: Union[str, None] = 'timeframe_period_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create stock_indicator table
    op.create_table(
        'stock_indicator',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('stock_id', sa.BigInteger(), nullable=False),
        sa.Column('indicator_key', sa.String(length=50), nullable=False),
        sa.Column('data', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['stock_id'], ['stocks.id'], ondelete='CASCADE'),
    )

    # Create unique constraint on (stock_id, indicator_key)
    op.create_unique_constraint('uq_stock_indicator_stock_key', 'stock_indicator', ['stock_id', 'indicator_key'])

    # Create indexes for efficient querying
    op.create_index('idx_stock_indicator_stock_id', 'stock_indicator', ['stock_id'], unique=False)
    op.create_index('idx_stock_indicator_key', 'stock_indicator', ['indicator_key'], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_stock_indicator_key', table_name='stock_indicator')
    op.drop_index('idx_stock_indicator_stock_id', table_name='stock_indicator')

    # Drop unique constraint
    op.drop_constraint('uq_stock_indicator_stock_key', 'stock_indicator', type_='unique')

    # Drop table
    op.drop_table('stock_indicator')