"""Update users and oauth_accounts tables

Revision ID: users_oauth_update
Revises: oauth_accounts
Create Date: 2026-04-30

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'users_oauth_update'
down_revision: Union[str, None] = 'oauth_accounts'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # === users 表新增欄位 ===
    op.add_column(
        'users',
        sa.Column('display_name', sa.String(255), nullable=True)
    )
    op.add_column(
        'users',
        sa.Column('picture_url', sa.String(500), nullable=True)
    )
    op.add_column(
        'users',
        sa.Column('quota', sa.Integer(), server_default='10', nullable=False)
    )
    op.add_column(
        'users',
        sa.Column('subscription_status', sa.String(50), server_default='free', nullable=False)
    )

    # === oauth_accounts 表新增欄位 ===
    op.add_column(
        'oauth_accounts',
        sa.Column('access_token', sa.String(500), nullable=True)
    )
    op.add_column(
        'oauth_accounts',
        sa.Column('refresh_token', sa.String(500), nullable=True)
    )
    op.add_column(
        'oauth_accounts',
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    # === 回滾 oauth_accounts ===
    op.drop_column('oauth_accounts', 'expires_at')
    op.drop_column('oauth_accounts', 'refresh_token')
    op.drop_column('oauth_accounts', 'access_token')

    # === 回滾 users ===
    op.drop_column('users', 'subscription_status')
    op.drop_column('users', 'quota')
    op.drop_column('users', 'picture_url')
    op.drop_column('users', 'display_name')
