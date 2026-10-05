from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import RoleName
from app.exceptions.task import TaskNotFoundException
from app.models.task import Task
from app.models.user import User
from app.repositories.tasks import TaskRepository
from app.schemas import (
    PaginatedResponse,
    PaginationMeta,
    TaskCreateRequest,
    TaskListQuery,
    TaskResponse,
    TaskUpdateRequest,
)


class TaskService:
    def __init__(self, session: AsyncSession) -> None:
        self.task_repository = TaskRepository(session)

    async def create_task(
        self,
        request: TaskCreateRequest,
        owner_id: UUID,
    ) -> TaskResponse:
        task = Task(
            owner_id=owner_id,
            title=request.title,
            description=request.description,
            status=request.status,
            priority=request.priority,
            due_date=request.due_date,
        )

        task = await self.task_repository.create(task)

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

        await self.task_repository.delete(task)
