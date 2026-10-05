"""add email verification otp support

Revision ID: 962c1734e81d
Revises: 7920f7cf42f4
Create Date: 2026-09-12 12:23:19.350853
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "962c1734e81d"
down_revision: str | Sequence[str] | None = "7920f7cf42f4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "email_otps",
        sa.Column(
            "user_id",
            sa.UUID(),
            nullable=False,
        ),
        sa.Column(
            "purpose",
            sa.Enum(
                "verify_email",
                "reset_password",
                name="email_otp_purpose",
            ),
            nullable=False,
        ),
        sa.Column(
            "otp_hash",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "used_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "invalidated_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "failed_attempts",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "id",
            sa.UUID(),
            nullable=False,
        ),
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
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f("ix_email_otps_purpose"),
        "email_otps",
        ["purpose"],
        unique=False,
    )

    op.create_index(
        op.f("ix_email_otps_user_id"),
        "email_otps",
        ["user_id"],
        unique=False,
    )

    # Add temporarily as nullable so existing users
    # can be safely backfilled.
    op.add_column(
        "users",
        sa.Column(
            "is_verified",
            sa.Boolean(),
            nullable=True,
        ),
    )

    # Existing Phase-1 users were already allowed to use
    # their accounts, so treat them as verified.
    op.execute(
        """
        UPDATE users
        SET is_verified = TRUE
        WHERE is_verified IS NULL
        """
    )

    # Final schema requires the value.
    op.alter_column(
        "users",
        "is_verified",
        existing_type=sa.Boolean(),
        nullable=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column(
        "users",
        "is_verified",
    )

    op.drop_index(
        op.f("ix_email_otps_user_id"),
        table_name="email_otps",
    )

    op.drop_index(
        op.f("ix_email_otps_purpose"),
        table_name="email_otps",
    )

    op.drop_table(
        "email_otps",
    )
    sa.Enum(
        "verify_email",
        "reset_password",
        name="email_otp_purpose",
    ).drop(op.get_bind())
