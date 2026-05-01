"""Add OAuth accounts and modify users

Revision ID: oauth_accounts
Revises: 2026-04-30_create_users_table
Create Date: 2026-04-30

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'oauth_accounts'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. 修改 users 表
    # 將 email 和 hashed_password 改為可選
    op.alter_column('users', 'email', existing_type=sa.String(255), nullable=True)
    op.alter_column('users', 'hashed_password', existing_type=sa.String(255), nullable=True)

    # 新增 line_user_id 欄位
    op.add_column('users', sa.Column('line_user_id', sa.String(50), nullable=True))
    op.create_index('ix_users_line_user_id', 'users', ['line_user_id'], unique=True)

    # 2. 建立 oauth_accounts 表
    op.create_table(
        'oauth_accounts',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('provider', sa.String(20), nullable=False),
        sa.Column('provider_user_id', sa.String(255), nullable=False),
        sa.Column('provider_email', sa.String(255), nullable=True),
        sa.Column('provider_name', sa.String(255), nullable=True),
        sa.Column('provider_picture', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), default=False, nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('provider', 'provider_user_id', name='uq_oauth_provider_user'),
    )
    op.create_index('ix_oauth_accounts_user_id', 'oauth_accounts', ['user_id'])


def downgrade() -> None:
    # 1. 刪除 oauth_accounts 表
    op.drop_index('ix_oauth_accounts_user_id', table_name='oauth_accounts')
    op.drop_table('oauth_accounts')

    # 2. 恢復 users 表
    op.drop_index('ix_users_line_user_id', table_name='users')
    op.drop_column('users', 'line_user_id')

    # 注意：這裡假設原本 email 和 hashed_password 都是 NOT NULL
    # 如果資料庫中有 NULL 值，需要先處理
    op.alter_column('users', 'hashed_password', existing_type=sa.String(255), nullable=False)
    op.alter_column('users', 'email', existing_type=sa.String(255), nullable=False)
