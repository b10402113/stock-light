"""create scheduled_reminders table

Revision ID: scheduled_reminders
Revises: ind_sub_enhance
Create Date: 2026-05-10

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'scheduled_reminders'
down_revision: Union[str, None] = 'ind_sub_enhance'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'scheduled_reminders',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('stock_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=50), nullable=False, server_default=''),
        sa.Column('message', sa.String(length=200), nullable=False, server_default=''),
        sa.Column('frequency_type', sa.String(length=10), nullable=False, server_default='daily'),
        sa.Column('reminder_time', sa.Time(), nullable=False, server_default='17:00:00'),
        sa.Column('day_of_week', sa.SmallInteger(), nullable=False, server_default='0'),
        sa.Column('day_of_month', sa.SmallInteger(), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('last_triggered_at', sa.DateTime(timezone=True), nullable=False, server_default='1970-01-01 00:00:00+00'),
        sa.Column('next_trigger_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['stock_id'], ['stocks.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('scheduled_reminders_user_id_idx', 'scheduled_reminders', ['user_id'], unique=False)
    op.create_index('scheduled_reminders_stock_id_idx', 'scheduled_reminders', ['stock_id'], unique=False)
    op.create_index('scheduled_reminders_is_active_idx', 'scheduled_reminders', ['is_active'], unique=False)
    op.create_index('scheduled_reminders_next_trigger_at_idx', 'scheduled_reminders', ['next_trigger_at'], unique=False)
    op.create_index(
        'scheduled_reminders_user_stock_unique_key',
        'scheduled_reminders',
        ['user_id', 'stock_id', 'frequency_type', 'reminder_time', 'day_of_week', 'day_of_month'],
        unique=True,
        postgresql_where=sa.text('is_deleted = false')
    )


def downgrade() -> None:
    op.drop_index('scheduled_reminders_user_stock_unique_key', table_name='scheduled_reminders', postgresql_where=sa.text('is_deleted = false'))
    op.drop_index('scheduled_reminders_next_trigger_at_idx', table_name='scheduled_reminders')
    op.drop_index('scheduled_reminders_is_active_idx', table_name='scheduled_reminders')
    op.drop_index('scheduled_reminders_stock_id_idx', table_name='scheduled_reminders')
    op.drop_index('scheduled_reminders_user_id_idx', table_name='scheduled_reminders')
    op.drop_table('scheduled_reminders')