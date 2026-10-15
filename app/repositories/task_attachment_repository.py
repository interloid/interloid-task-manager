from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task_attachment import TaskAttachment
from app.repositories.base import BaseRepository


class TaskAttachmentRepository(BaseRepository[TaskAttachment]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, TaskAttachment)

    async def get_by_task(
        self,
        task_id: UUID,
    ) -> list[TaskAttachment]:
        stmt = (
            select(TaskAttachment)
            .where(TaskAttachment.task_id == task_id)
            .order_by(TaskAttachment.created_at.desc())
        )

        result = await self.session.execute(stmt)

        return list(result.scalars().all())

    async def get_by_id_and_task(
        self,
        attachment_id: UUID,
        task_id: UUID,
    ) -> TaskAttachment | None:
        stmt = select(TaskAttachment).where(
            TaskAttachment.id == attachment_id,
            TaskAttachment.task_id == task_id,
        )

        result = await self.session.execute(stmt)

        return result.scalar_one_or_none()
