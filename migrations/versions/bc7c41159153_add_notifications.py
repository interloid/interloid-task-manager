"""add notifications

Revision ID: bc7c41159153
Revises: da23e6dfe7fa
Create Date: 2026-10-22 12:12:46.733238
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "bc7c41159153"
down_revision: str | Sequence[str] | None = "da23e6dfe7fa"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "notifications",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("task_id", sa.UUID(), nullable=True),
        sa.Column(
            "type",
            sa.Enum(
                "task_assigned",
                "task_commented",
                name="notification_type",
            ),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "unread",
                "read",
                name="notification_status",
            ),
            server_default="unread",
            nullable=False,
        ),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["task_id"],
            ["tasks.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f("ix_notifications_status"),
        "notifications",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_notifications_task_id"),
        "notifications",
        ["task_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_notifications_user_id"),
        "notifications",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f("ix_notifications_user_id"),
        table_name="notifications",
    )
    op.drop_index(
        op.f("ix_notifications_task_id"),
        table_name="notifications",
    )
    op.drop_index(
        op.f("ix_notifications_status"),
        table_name="notifications",
    )
    op.drop_table("notifications")

    bind = op.get_bind()
    sa.Enum(name="notification_type").drop(bind, checkfirst=True)
    sa.Enum(name="notification_status").drop(bind, checkfirst=True)
