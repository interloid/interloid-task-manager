from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.enums import RoleName
from app.models.base_model import BaseModelMixin

if TYPE_CHECKING:
    from app.models import OAuthAccount, RefreshToken, Task, TaskAttachment, TaskComment


class User(BaseModelMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=True,
    )

    first_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    last_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    role: Mapped[RoleName] = mapped_column(
        Enum(
            RoleName,
            name="role_name",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=RoleName.USER,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    password_changed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    tasks: Mapped[list["Task"]] = relationship(
        back_populates="owner",
        cascade="all, delete-orphan",
    )

    oauth_accounts: Mapped[list["OAuthAccount"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    task_attachments: Mapped[list["TaskAttachment"]] = relationship(
        back_populates="uploaded_by",
    )

    comments: Mapped[list["TaskComment"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
