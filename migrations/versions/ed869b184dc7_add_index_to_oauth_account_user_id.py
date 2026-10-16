"""add index to oauth account user id

Revision ID: ed869b184dc7
Revises: e664451bd0ea
Create Date: 2026-10-15 20:23:40.251076
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ed869b184dc7"
down_revision: str | Sequence[str] | None = "e664451bd0ea"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add an index on oauth_accounts.user_id."""
    op.create_index(
        op.f("ix_oauth_accounts_user_id"),
        "oauth_accounts",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    """Remove the index on oauth_accounts.user_id."""
    op.drop_index(
        op.f("ix_oauth_accounts_user_id"),
        table_name="oauth_accounts",
    )
