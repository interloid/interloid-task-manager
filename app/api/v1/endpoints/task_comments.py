from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.responses import (
    NOT_FOUND_RESPONSE,
    UNAUTHORIZED_RESPONSE,
    VALIDATION_ERROR_RESPONSE,
    NOT_FOUND_RESPONSE,
)
from app.db.dependencies import get_db
from app.models import User
from app.repositories import (
    NotificationRepository,
    TaskCommentRepository,
    TaskRepository,
)
from app.schemas import (
    APIResponse,
    MessageResponse,
    PaginatedResponse,
    TaskCommentCreateRequest,
    TaskCommentResponse,
    TaskCommentUpdateRequest,
)
from app.services.notification import NotificationService
from app.services.task_comment_service import TaskCommentService

router = APIRouter(
    prefix="/tasks",
    tags=["Task Comments"],
)


def get_task_comment_service(
    db: AsyncSession,
) -> TaskCommentService:
    return TaskCommentService(
        task_repository=TaskRepository(db),
        comment_repository=TaskCommentRepository(db),
        notification_service=NotificationService(
            notification_repository=NotificationRepository(db),
            task_repository=TaskRepository(db),
        ),
    )


@router.post(
    "/{task_id}/comments",
    response_model=APIResponse[TaskCommentResponse],
    status_code=status.HTTP_201_CREATED,
    responses={
        **UNAUTHORIZED_RESPONSE,
        **NOT_FOUND_RESPONSE,
        **VALIDATION_ERROR_RESPONSE,
    },
)
async def create_task_comment(
    task_id: UUID,
    request: TaskCommentCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db, scope="function")],
) -> APIResponse[TaskCommentResponse]:
    service = get_task_comment_service(db)

    comment = await service.create_comment(
        task_id=task_id,
        current_user=current_user,
        request=request,
    )

    return APIResponse(
        message="comment created successfully",
        data=comment,
    )


@router.get(
    "/{task_id}/comments",
    response_model=PaginatedResponse[TaskCommentResponse],
    status_code=status.HTTP_200_OK,
    responses={
        **UNAUTHORIZED_RESPONSE,
        **NOT_FOUND_RESPONSE,
    },
)
async def list_task_comments(
    task_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db, scope="function")],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PaginatedResponse[TaskCommentResponse]:
    service = get_task_comment_service(db)

    return await service.list_comments(
        task_id=task_id,
        current_user=current_user,
        page=page,
        page_size=page_size,
    )


@router.patch(
    "/{task_id}/comments/{comment_id}",
    response_model=APIResponse[TaskCommentResponse],
    status_code=status.HTTP_200_OK,
    responses={
        **UNAUTHORIZED_RESPONSE,
        **VALIDATION_ERROR_RESPONSE,
        **NOT_FOUND_RESPONSE,
    },
)
async def update_task_comment(
    task_id: UUID,
    comment_id: UUID,
    request: TaskCommentUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db, scope="function")],
) -> APIResponse[TaskCommentResponse]:
    service = get_task_comment_service(db)

    comment = await service.update_comment(
        task_id=task_id,
        comment_id=comment_id,
        current_user=current_user,
        request=request,
    )

    return APIResponse(
        message="Comment updated successfully",
        data=comment,
    )


@router.delete(
    "/{task_id}/comments/{comment_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    responses={
        **UNAUTHORIZED_RESPONSE,
        **NOT_FOUND_RESPONSE,
    },
)
async def delete_task_comment(
    task_id: UUID,
    comment_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db, scope="function")],
) -> MessageResponse:
    service = get_task_comment_service(db)

    await service.delete_comment(
        task_id=task_id,
        comment_id=comment_id,
        current_user=current_user,
    )

    return MessageResponse(message="Comment deleted successfully")
