from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_task_list_query
from app.api.responses import (
    NOT_FOUND_RESPONSE,
    UNAUTHORIZED_RESPONSE,
    VALIDATION_ERROR_RESPONSE,
)
from app.db.dependencies import get_db
from app.models.user import User
from app.schemas import (
    APIResponse,
    MessageResponse,
    PaginatedResponse,
    TaskCreateRequest,
    TaskListQuery,
    TaskResponse,
    TaskUpdateRequest,
)
from app.services.task import TaskService

router = APIRouter(
    prefix="/tasks",
    tags=["Tasks"],
)


@router.post(
    "",
    response_model=APIResponse[TaskResponse],
    status_code=status.HTTP_201_CREATED,
    responses={
        **UNAUTHORIZED_RESPONSE,
        **VALIDATION_ERROR_RESPONSE,
    },
)
async def create_task(
    request: TaskCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db, scope="function"),
) -> APIResponse[TaskResponse]:
    service = TaskService(db)

    task = await service.create_task(
        request=request,
        owner_id=current_user.id,
    )

    return APIResponse(
        message="Task created successfully",
        data=task,
    )


@router.get(
    "",
    response_model=PaginatedResponse[TaskResponse],
    status_code=status.HTTP_200_OK,
    responses={
        **UNAUTHORIZED_RESPONSE,
        **VALIDATION_ERROR_RESPONSE,
    },
)
async def get_tasks(
    query: Annotated[
        TaskListQuery,
        Depends(get_task_list_query),
    ],
    current_user: Annotated[
        User,
        Depends(get_current_user),
    ],
    db: Annotated[
        AsyncSession,
        Depends(get_db, scope="function"),
    ],
) -> PaginatedResponse[TaskResponse]:
    service = TaskService(db)

    return await service.get_tasks(
        current_user=current_user,
        query=query,
    )


@router.get(
    "/{id}",
    response_model=APIResponse[TaskResponse],
    status_code=status.HTTP_200_OK,
    responses={
        **UNAUTHORIZED_RESPONSE,
        **NOT_FOUND_RESPONSE,
        **VALIDATION_ERROR_RESPONSE,
    },
)
async def get_task_by_id(
    id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db, scope="function"),
) -> APIResponse[TaskResponse]:
    service = TaskService(db)

    task = await service.get_task_by_id(
        id=id,
        current_user=current_user,
    )

    return APIResponse(
        message="Task fetched successfully",
        data=task,
    )


@router.patch(
    "/{id}",
    response_model=APIResponse[TaskResponse],
    status_code=status.HTTP_200_OK,
    responses={
        **UNAUTHORIZED_RESPONSE,
        **NOT_FOUND_RESPONSE,
        **VALIDATION_ERROR_RESPONSE,
    },
)
async def update_task(
    id: UUID,
    request: TaskUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db, scope="function"),
) -> APIResponse[TaskResponse]:
    service = TaskService(db)

    task = await service.update_task(
        id=id,
        current_user=current_user,
        request=request,
    )

    return APIResponse(
        message="Task updated successfully",
        data=task,
    )


@router.delete(
    "/{id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    responses={
        **UNAUTHORIZED_RESPONSE,
        **NOT_FOUND_RESPONSE,
        **VALIDATION_ERROR_RESPONSE,
    },
)
async def delete_task(
    id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db, scope="function"),
) -> MessageResponse:
    service = TaskService(db)

    await service.delete_task(
        id=id,
        current_user=current_user,
    )

    return MessageResponse(
        message="Task deleted successfully",
    )
