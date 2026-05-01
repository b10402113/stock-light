"""create stocks table

Revision ID: stocks_table
Revises: users_oauth_update
Create Date: 2026-05-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'stocks_table'
down_revision: Union[str, None] = 'users_oauth_update'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create stocks table
    op.create_table(
        'stocks',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('symbol', sa.String(length=20), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('current_price', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('calculated_indicators', postgresql.JSONB(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.PrimaryKeyConstraint('id'),
    )

    # Create unique index on symbol
    op.create_index('stocks_symbol_idx', 'stocks', ['symbol'], unique=True)

    # Create index on is_active
    op.create_index('stocks_is_active_idx', 'stocks', ['is_active'], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index('stocks_is_active_idx', table_name='stocks')
    op.drop_index('stocks_symbol_idx', table_name='stocks')

    # Drop table
    op.drop_table('stocks')
