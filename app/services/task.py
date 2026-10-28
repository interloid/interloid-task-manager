from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.enums import NotificationType, RoleName
from app.exceptions.task import TaskNotFoundException
from app.exceptions.user import UserNotFoundException
from app.models.task import Task
from app.models.user import User
from app.repositories import (
    NotificationRepository,
    TaskAttachmentRepository,
    TaskRepository,
    UserRepository,
)
from app.schemas import (
    PaginatedResponse,
    PaginationMeta,
    TaskCreateRequest,
    TaskListQuery,
    TaskResponse,
    TaskUpdateRequest,
)
from app.services.notification import NotificationService
from app.services.s3_storage_service import S3StorageService
from app.workers.email_queue import enqueue_email


class TaskService:
    def __init__(self, session: AsyncSession) -> None:
        self.user_repository = UserRepository(session)
        self.task_repository = TaskRepository(session)
        self.attachment_repository = TaskAttachmentRepository(session)
        self.storage_service = S3StorageService()

        self.notification_service = NotificationService(
            notification_repository=NotificationRepository(session),
            task_repository=self.task_repository,
        )

    async def create_task(
        self,
        request: TaskCreateRequest,
        current_user: User,
    ) -> TaskResponse:
        owner_id = current_user.id
        assigned_user: User | None = None

        if current_user.role == RoleName.ADMIN and request.owner_id is not None:
            owner = await self.user_repository.get_by_id(request.owner_id)

            if owner is None:
                raise UserNotFoundException()

            owner_id = owner.id

            if owner_id != current_user.id:
                assigned_user = owner

        task = Task(
            owner_id=owner_id,
            title=request.title,
            description=request.description,
            status=request.status,
            priority=request.priority,
            due_date=request.due_date,
        )

        task = await self.task_repository.create(task)

        if assigned_user is not None:
            await self.notification_service.create_notification(
                recipient_id=assigned_user.id,
                task_id=task.id,
                notification_type=NotificationType.TASK_ASSIGNED,
                title="New task assigned to you",
                message=f"A new task '{task.title}' has been assigned to you.",
            )
            await enqueue_email(
                to_email=assigned_user.email,
                subject="A new task has been assigned to you",
                text_body=(
                    f"Hello,\n\n"
                    f"A new task '{task.title}' has been assigned to you.\n\n"
                    "Please log in to the Task Manager to review the task."
                ),
                html_body=(
                    "<h2>A new task has been assigned to you</h2>"
                    f"<p>A new task <strong>{task.title}</strong> "
                    "has been assigned to you.</p>"
                    "<p>Please log in to the Task Manager "
                    "to review the task.</p>"
                ),
            )

        return TaskResponse.model_validate(task)

    async def get_tasks(
        self,
        *,
        current_user: User,
        query: TaskListQuery,
    ) -> PaginatedResponse[TaskResponse]:
        owner_id: UUID | None

        if current_user.role == RoleName.ADMIN:
            owner_id = query.owner_id
        else:
            owner_id = current_user.id

        offset = (query.page - 1) * query.page_size

        tasks, total = await self.task_repository.get_tasks(
            owner_id=owner_id,
            status=query.status,
            priority=query.priority,
            due_from=query.due_from,
            due_to=query.due_to,
            search=query.search,
            limit=query.page_size,
            offset=offset,
            sort_by=query.sort_by,
            order=query.order,
        )

        total_pages = (total + query.page_size - 1) // query.page_size

        data = [TaskResponse.model_validate(task) for task in tasks]

        return PaginatedResponse(
            message="Tasks retrieved successfully",
            data=data,
            pagination=PaginationMeta(
                page=query.page,
                page_size=query.page_size,
                total=total,
                total_pages=total_pages,
            ),
        )

    async def get_task_by_id(
        self,
        *,
        id: UUID,
        current_user: User,
    ) -> TaskResponse:
        task = await self.task_repository.get_by_id(id)

        if task is None:
            raise TaskNotFoundException()

        if current_user.role != RoleName.ADMIN and task.owner_id != current_user.id:
            raise TaskNotFoundException()

        return TaskResponse.model_validate(task)

    async def update_task(
        self,
        *,
        id: UUID,
        current_user: User,
        request: TaskUpdateRequest,
    ) -> TaskResponse:
        task = await self.task_repository.get_by_id(id)

        if task is None:
            raise TaskNotFoundException()

        if current_user.role != RoleName.ADMIN and task.owner_id != current_user.id:
            raise TaskNotFoundException()

        update_data = request.model_dump(
            exclude_unset=True,
        )

        for field, value in update_data.items():
            setattr(task, field, value)

        updated_task = await self.task_repository.update(task)

        return TaskResponse.model_validate(updated_task)

    async def delete_task(
        self,
        *,
        id: UUID,
        current_user: User,
    ) -> None:
        task = await self.task_repository.get_by_id(id)

        if task is None:
            raise TaskNotFoundException()

        if current_user.role != RoleName.ADMIN and task.owner_id != current_user.id:
            raise TaskNotFoundException()

        storage_keys = await self.attachment_repository.get_storage_keys_by_task(id)

        for storage_key in storage_keys:
            await run_in_threadpool(
                self.storage_service.delete_file,
                storage_key,
            )

        await self.task_repository.delete(task)
