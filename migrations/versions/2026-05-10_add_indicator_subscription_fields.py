"""add title, message, signal_type to indicator_subscriptions

Revision ID: ind_sub_enhance
Revises: plans_tables
Create Date: 2026-05-10

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ind_sub_enhance'
down_revision: Union[str, None] = 'plans_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add title column (VARCHAR 50, NOT NULL with DEFAULT '')
    op.add_column(
        'indicator_subscriptions',
        sa.Column('title', sa.String(length=50), nullable=False, server_default='')
    )

    # Add message column (VARCHAR 200, NOT NULL with DEFAULT '')
    op.add_column(
        'indicator_subscriptions',
        sa.Column('message', sa.String(length=200), nullable=False, server_default='')
    )

    # Add signal_type column (VARCHAR 10, NOT NULL with DEFAULT 'buy')
    op.add_column(
        'indicator_subscriptions',
        sa.Column('signal_type', sa.String(length=10), nullable=False, server_default='buy')
    )


def downgrade() -> None:
    # Drop columns in reverse order
    op.drop_column('indicator_subscriptions', 'signal_type')
    op.drop_column('indicator_subscriptions', 'message')
    op.drop_column('indicator_subscriptions', 'title')