from uuid import UUID

from app.enums import RoleName
from app.exceptions.task import TaskNotFoundException
from app.exceptions.task_comment import TaskCommentNotFoundException
from app.models import TaskComment, User, Task
from app.repositories import TaskCommentRepository, TaskRepository
from app.schemas import (
    PaginatedResponse,
    PaginationMeta,
    TaskCommentCreateRequest,
    TaskCommentResponse,
    TaskCommentUpdateRequest,
)


class TaskCommentService:
    def __init__(
        self,
        task_repository: TaskRepository,
        comment_repository: TaskCommentRepository,
    ) -> None:
        self.task_repository = task_repository
        self.comment_repository = comment_repository

    async def create_comment(
        self,
        *,
        task_id: UUID,
        current_user: User,
        request: TaskCommentCreateRequest,
    ) -> TaskCommentResponse:
        await self._get_authorized_task(
            task_id=task_id,
            current_user=current_user,
        )

        comment = TaskComment(
            task_id=task_id,
            user_id=current_user.id,
            content=request.content,
        )

        comment = await self.comment_repository.create(comment)

        return TaskCommentResponse.model_validate(comment)

    async def list_comments(
        self,
        *,
        task_id: UUID,
        current_user: User,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResponse[TaskCommentResponse]:
        await self._get_authorized_task(
            task_id=task_id,
            current_user=current_user,
        )

        offset = (page - 1) * page_size

        comments, total = await self.comment_repository.get_by_task(
            task_id,
            limit=page_size,
            offset=offset,
        )

        data = [TaskCommentResponse.model_validate(comment) for comment in comments]

        total_pages = (total + page_size - 1) // page_size

        return PaginatedResponse(
            message="Comments retrieved successfully",
            data=data,
            pagination=PaginationMeta(
                page=page,
                page_size=page_size,
                total=total,
                total_pages=total_pages,
            ),
        )

    async def update_comment(
        self,
        *,
        task_id: UUID,
        comment_id: UUID,
        current_user: User,
        request: TaskCommentUpdateRequest,
    ) -> TaskCommentResponse:
        await self._get_authorized_task(
            task_id=task_id,
            current_user=current_user,
        )

        comment = await self._get_comment(
            task_id=task_id,
            comment_id=comment_id,
        )

        if current_user.role != RoleName.ADMIN and comment.user_id != current_user.id:
            raise TaskCommentNotFoundException()

        comment.content = request.content

        updated_comment = await self.comment_repository.update(comment)

        return TaskCommentResponse.model_validate(updated_comment)

    async def delete_comment(
        self,
        *,
        task_id: UUID,
        comment_id: UUID,
        current_user: User,
    ) -> None:
        await self._get_authorized_task(
            task_id=task_id,
            current_user=current_user,
        )

        comment = await self._get_comment(
            task_id=task_id,
            comment_id=comment_id,
        )

        if current_user.role != RoleName.ADMIN and comment.user_id != current_user.id:
            raise TaskCommentNotFoundException()

        await self.comment_repository.delete(comment)

    async def _get_authorized_task(
        self,
        *,
        task_id: UUID,
        current_user: User,
    ) -> Task :
        task = await self.task_repository.get_by_id(task_id)

        if task is None:
            raise TaskNotFoundException()

        if current_user.role != RoleName.ADMIN and task.owner_id != current_user.id:
            raise TaskNotFoundException()

        return task

    async def _get_comment(
        self,
        *,
        task_id: UUID,
        comment_id: UUID,
    ) -> TaskComment:
        comment = await self.comment_repository.get_by_id_and_task(
            comment_id=comment_id,
            task_id=task_id,
        )

        if comment is None:
            raise TaskCommentNotFoundException()

        return comment
