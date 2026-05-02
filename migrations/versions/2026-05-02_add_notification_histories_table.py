"""add notification_histories table

Revision ID: 71299690ed69
Revises: indicator_subscriptions
Create Date: 2026-05-02 09:25:58.897464

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '71299690ed69'
down_revision: Union[str, None] = 'indicator_subscriptions'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'notification_histories',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('indicator_subscription_id', sa.Integer(), nullable=False),
        sa.Column('triggered_value', sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column('send_status', sa.String(length=20), nullable=False),
        sa.Column('line_message_id', sa.String(length=100), nullable=True),
        sa.Column('triggered_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['indicator_subscription_id'], ['indicator_subscriptions.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('notification_histories_user_id_idx', 'notification_histories', ['user_id'], unique=False)
    op.create_index('notification_histories_indicator_subscription_id_idx', 'notification_histories', ['indicator_subscription_id'], unique=False)
    op.create_index('notification_histories_triggered_at_idx', 'notification_histories', ['triggered_at'], unique=False)
    op.create_index('notification_histories_send_status_idx', 'notification_histories', ['send_status'], unique=False)
    op.create_index('notification_histories_user_triggered_idx', 'notification_histories', ['user_id', sa.literal_column('triggered_at DESC')], unique=False)


def downgrade() -> None:
    op.drop_index('notification_histories_user_triggered_idx', table_name='notification_histories')
    op.drop_index('notification_histories_send_status_idx', table_name='notification_histories')
    op.drop_index('notification_histories_triggered_at_idx', table_name='notification_histories')
    op.drop_index('notification_histories_indicator_subscription_id_idx', table_name='notification_histories')
    op.drop_index('notification_histories_user_id_idx', table_name='notification_histories')
    op.drop_table('notification_histories')