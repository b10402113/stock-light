"""add source and market fields to stocks table

Revision ID: stock_source_market
Revises: 71299690ed69
Create Date: 2026-05-06

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'stock_source_market'
down_revision: Union[str, None] = '71299690ed69'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add source column with default value 1 (FUGLE)
    op.add_column(
        'stocks',
        sa.Column(
            'source',
            sa.SmallInteger(),
            nullable=False,
            server_default='1'
        )
    )

    # Add market column with default value 1 (TAIWAN)
    op.add_column(
        'stocks',
        sa.Column(
            'market',
            sa.SmallInteger(),
            nullable=False,
            server_default='1'
        )
    )


def downgrade() -> None:
    # Drop market column
    op.drop_column('stocks', 'market')

    # Drop source column
    op.drop_column('stocks', 'source')