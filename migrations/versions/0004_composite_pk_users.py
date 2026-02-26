"""Composite PK (telegram_id, bot_token) for users

Revision ID: 0004
Revises: 0003
Create Date: 2026-02-27 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop FK on channel_events that references users.telegram_id (single-column).
    # After this migration telegram_id is no longer unique on its own, so the FK
    # cannot be enforced as-is. We keep the column for lookup but drop the constraint.
    op.drop_constraint(
        "channel_events_user_id_fkey", "channel_events", type_="foreignkey"
    )

    # Replace NULL bot_token with empty string to preserve "orphaned" rows
    op.execute("UPDATE users SET bot_token = '' WHERE bot_token IS NULL")

    # Drop old single-column primary key
    op.drop_constraint("users_pkey", "users", type_="primary")

    # Make bot_token NOT NULL
    op.alter_column("users", "bot_token", nullable=False)

    # Drop old index (will be covered by the new PK)
    op.execute("DROP INDEX IF EXISTS ix_users_bot_token")

    # Create composite primary key
    op.create_primary_key("users_pkey", "users", ["telegram_id", "bot_token"])


def downgrade() -> None:
    # Drop composite PK
    op.drop_constraint("users_pkey", "users", type_="primary")

    # Restore bot_token as nullable
    op.alter_column("users", "bot_token", nullable=True)

    # Rows with duplicate telegram_id must be removed before restoring single-column PK
    op.execute(
        """
        DELETE FROM users
        WHERE ctid NOT IN (
            SELECT min(ctid)
            FROM users
            GROUP BY telegram_id
        )
        """
    )

    # Restore old single-column PK on telegram_id
    op.create_primary_key("users_pkey", "users", ["telegram_id"])

    # Restore index
    op.create_index("ix_users_bot_token", "users", ["bot_token"])

    # Restore FK on channel_events
    op.create_foreign_key(
        "channel_events_user_id_fkey",
        "channel_events",
        "users",
        ["user_id"],
        ["telegram_id"],
        ondelete="CASCADE",
    )
