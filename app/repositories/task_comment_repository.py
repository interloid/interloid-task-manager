from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task_comment import TaskComment
from app.repositories.base import BaseRepository


class TaskCommentRepository(BaseRepository[TaskComment]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, TaskComment)

    async def get_by_task(
        self,
        task_id: UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[TaskComment], int]:
        count_stmt = (
            select(func.count())
            .select_from(TaskComment)
            .where(TaskComment.task_id == task_id)
        )

        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar_one()

        stmt = (
            select(TaskComment)
            .where(TaskComment.task_id == task_id)
            .order_by(
                TaskComment.created_at.desc(),
                TaskComment.id.desc(),
            )
            .limit(limit)
            .offset(offset)
        )

        result = await self.session.execute(stmt)
        comments = list(result.scalars().all())

        return comments, total

    async def get_by_id_and_task(
        self,
        comment_id: UUID,
        task_id: UUID,
    ) -> TaskComment | None:
        stmt = select(TaskComment).where(
            TaskComment.id == comment_id,
            TaskComment.task_id == task_id,
        )

        result = await self.session.execute(stmt)

        return result.scalar_one_or_none()

    async def update(
        self,
        comment: TaskComment,
    ) -> TaskComment:
        await self.session.flush()
        await self.session.refresh(comment)

        return comment
