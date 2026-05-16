"""set database timezone to Asia/Taipei and convert existing timestamps

Revision ID: 20260516_set_timezone
Revises:
Create Date: 2026-05-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260516_set_timezone'
down_revision: Union[str, None] = 'simplify_indicator_subscription'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Set timezone to Asia/Taipei and convert existing UTC timestamps."""

    # Step 1: Set database timezone to Asia/Taipei
    op.execute("ALTER DATABASE stocklight SET timezone TO 'Asia/Taipei';")

    # Step 2: Convert existing timestamp columns from UTC to Asia/Taipei
    # All tables with created_at/updated_at from Base model
    tables_with_base_timestamps = [
        'users',
        'stocks',
        'stock_indicator',
        'indicator_subscriptions',
        'watchlists',
        'watchlist_stocks',
        'notification_histories',
        'scheduled_reminders',
        'plans',
        'daily_prices',
    ]

    # Tables with additional timestamp columns
    tables_with_additional_timestamps = {
        'indicator_subscriptions': ['cooldown_end_at'],
        'scheduled_reminders': ['next_trigger_at', 'last_triggered_at'],
        'plans': ['due_date'],
        'oauth_accounts': ['expires_at'],
    }

    # Convert base timestamps (created_at, updated_at)
    for table in tables_with_base_timestamps:
        op.execute(f"""
            UPDATE {table}
            SET created_at = created_at + INTERVAL '8 hours',
                updated_at = updated_at + INTERVAL '8 hours'
            WHERE created_at IS NOT NULL;
        """)

    # Convert additional timestamp columns
    for table, columns in tables_with_additional_timestamps.items():
        for column in columns:
            op.execute(f"""
                UPDATE {table}
                SET {column} = {column} + INTERVAL '8 hours'
                WHERE {column} IS NOT NULL;
            """)

    # Step 3: Update server_default for timestamp columns to use Asia/Taipei timezone
    # This will ensure new records use Asia/Taipei timezone
    for table in tables_with_base_timestamps:
        op.execute(f"""
            ALTER TABLE {table}
            ALTER COLUMN created_at SET DEFAULT (now() AT TIME ZONE 'Asia/Taipei'),
            ALTER COLUMN updated_at SET DEFAULT (now() AT TIME ZONE 'Asia/Taipei');
        """)


def downgrade() -> None:
    """Revert timezone to UTC and convert timestamps back."""

    # Step 1: Reset database timezone to UTC
    op.execute("ALTER DATABASE stocklight SET timezone TO 'UTC';")

    # Step 2: Convert timestamps back from Asia/Taipei to UTC (-8 hours)
    tables_with_base_timestamps = [
        'users',
        'stocks',
        'stock_indicator',
        'indicator_subscriptions',
        'watchlists',
        'watchlist_stocks',
        'notification_histories',
        'scheduled_reminders',
        'plans',
        'daily_prices',
    ]

    tables_with_additional_timestamps = {
        'indicator_subscriptions': ['cooldown_end_at'],
        'scheduled_reminders': ['next_trigger_at', 'last_triggered_at'],
        'plans': ['due_date'],
        'oauth_accounts': ['expires_at'],
    }

    # Convert base timestamps back
    for table in tables_with_base_timestamps:
        op.execute(f"""
            UPDATE {table}
            SET created_at = created_at - INTERVAL '8 hours',
                updated_at = updated_at - INTERVAL '8 hours'
            WHERE created_at IS NOT NULL;
        """)

    # Convert additional timestamp columns back
    for table, columns in tables_with_additional_timestamps.items():
        for column in columns:
            op.execute(f"""
                UPDATE {table}
                SET {column} = {column} - INTERVAL '8 hours'
                WHERE {column} IS NOT NULL;
            """)

    # Step 3: Reset server_default to UTC
    for table in tables_with_base_timestamps:
        op.execute(f"""
            ALTER TABLE {table}
            ALTER COLUMN created_at SET DEFAULT (now() AT TIME ZONE 'UTC'),
            ALTER COLUMN updated_at SET DEFAULT (now() AT TIME ZONE 'UTC');
        """)