import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base_model import BaseModelMixin

if TYPE_CHECKING:
    from app.models import Task, User


class TaskComment(BaseModelMixin, Base):
    __tablename__ = "task_comments"

    task_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    task: Mapped["Task"] = relationship(
        back_populates="comments",
    )

    user: Mapped["User"] = relationship(
        back_populates="comments",
    )
