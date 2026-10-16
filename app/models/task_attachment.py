import uuid
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base_model import BaseModelMixin

if TYPE_CHECKING:
    from app.models import Task, User


class TaskAttachment(BaseModelMixin, Base):
    __tablename__ = "task_attachments"

    task_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    uploaded_by_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    original_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    storage_key: Mapped[str] = mapped_column(
        String(1024),
        nullable=False,
        unique=True,
    )

    content_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    file_size: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    task: Mapped["Task"] = relationship(
        back_populates="attachments",
    )

    uploaded_by: Mapped["User"] = relationship(
        back_populates="task_attachments",
    )
