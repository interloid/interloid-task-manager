"""merge file uploads and oauth index migrations

Revision ID: 5e2b84c536fb
Revises: e385dc8cf006, ed869b184dc7
Create Date: 2026-10-16 17:33:04.700712
"""

from collections.abc import Sequence

revision: str = "5e2b84c536fb"
down_revision: str | Sequence[str] | None = (
    "e385dc8cf006",
    "ed869b184dc7",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Merge migration branches."""
    pass


def downgrade() -> None:
    """Merge migration branches."""
    pass
