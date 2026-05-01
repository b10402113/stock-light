"""create watchlists tables

Revision ID: watchlists_tables
Revises: stocks_table
Create Date: 2026-05-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'watchlists_tables'
down_revision: Union[str, None] = 'stocks_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create watchlists table
    op.create_table(
        'watchlists',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False, server_default='My Watchlist'),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.PrimaryKeyConstraint('id'),
    )

    # Create indexes for watchlists
    op.create_index('watchlists_user_id_idx', 'watchlists', ['user_id'], unique=False)
    # Create unique partial index for (user_id, name) where is_deleted = false
    op.execute(
        "CREATE UNIQUE INDEX watchlists_user_id_name_key ON watchlists (user_id, name) "
        "WHERE is_deleted = false"
    )

    # Create watchlist_stocks table
    op.create_table(
        'watchlist_stocks',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('watchlist_id', sa.Integer(), sa.ForeignKey('watchlists.id'), nullable=False),
        sa.Column('stock_id', sa.Integer(), sa.ForeignKey('stocks.id'), nullable=False),
        sa.Column('notes', sa.String(length=500), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.PrimaryKeyConstraint('id'),
    )

    # Create indexes for watchlist_stocks
    op.create_index('watchlist_stocks_watchlist_id_idx', 'watchlist_stocks', ['watchlist_id'], unique=False)
    op.create_index('watchlist_stocks_stock_id_idx', 'watchlist_stocks', ['stock_id'], unique=False)
    # Create unique partial index for (watchlist_id, stock_id) where is_deleted = false
    op.execute(
        "CREATE UNIQUE INDEX watchlist_stocks_watchlist_stock_key ON watchlist_stocks (watchlist_id, stock_id) "
        "WHERE is_deleted = false"
    )


def downgrade() -> None:
    # Drop watchlist_stocks table
    op.execute("DROP INDEX IF EXISTS watchlist_stocks_watchlist_stock_key")
    op.drop_index('watchlist_stocks_stock_id_idx', table_name='watchlist_stocks')
    op.drop_index('watchlist_stocks_watchlist_id_idx', table_name='watchlist_stocks')
    op.drop_table('watchlist_stocks')

    # Drop watchlists table
    op.execute("DROP INDEX IF EXISTS watchlists_user_id_name_key")
    op.drop_index('watchlists_user_id_idx', table_name='watchlists')
    op.drop_table('watchlists')
