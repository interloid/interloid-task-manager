from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.responses import (
    UNAUTHORIZED_RESPONSE,
    VALIDATION_ERROR_RESPONSE,
)
from app.db.dependencies import get_db
from app.models import User
from app.repositories import NotificationRepository, TaskRepository
from app.schemas import (
    APIResponse,
    MessageResponse,
    NotificationListQuery,
    NotificationResponse,
    PaginatedResponse,
)
from app.services.notification import NotificationService

router = APIRouter(
    prefix="/notifications",
    tags=["Notifications"],
)


def get_notification_service(
    db: AsyncSession,
) -> NotificationService:
    return NotificationService(
        notification_repository=NotificationRepository(db),
        task_repository=TaskRepository(db),
    )


@router.get(
    "",
    response_model=PaginatedResponse[NotificationResponse],
    responses={
        **UNAUTHORIZED_RESPONSE,
        **VALIDATION_ERROR_RESPONSE,
    },
)
async def get_notifications(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db, scope="function")],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    is_read: bool | None = Query(default=None),
) -> PaginatedResponse[NotificationResponse]:
    service = get_notification_service(db)

    Query = NotificationListQuery(
        page=page,
        page_size=page_size,
        is_read=is_read,
    )

    return await service.get_user_notifications(
        current_user=current_user,
        query=Query,
    )


@router.patch(
    "/{id}/read",
    response_model=APIResponse[NotificationResponse],
    responses={
        **UNAUTHORIZED_RESPONSE,
        **VALIDATION_ERROR_RESPONSE,
    },
)
async def mark_notification_as_read(
    id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db, scope="function")],
) -> APIResponse[NotificationResponse]:
    service = get_notification_service(db)

    notification = await service.mark_notification_as_read(
        current_user=current_user,
        notification_id=id,
    )

    return APIResponse(
        message="Notification marked as read successfully",
        data=notification,
    )


@router.get(
    "/unread-count",
    response_model=APIResponse[dict[str, int]],
    responses={
        **UNAUTHORIZED_RESPONSE,
        **VALIDATION_ERROR_RESPONSE,
    },
)
async def get_unread_notification_count(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db, scope="function")],
) -> APIResponse[dict[str, int]]:
    service = get_notification_service(db)

    unread_count = await service.get_unread_notification_count(
        current_user=current_user,
    )

    return APIResponse(
        message="Unread notification count retrieved successfully",
        data={"unread_count": unread_count},
    )


@router.patch(
    "/read-all",
    response_model=APIResponse[dict[str, int]],
    responses={
        **UNAUTHORIZED_RESPONSE,
        **VALIDATION_ERROR_RESPONSE,
    },
)
async def mark_all_notifications_as_read(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db, scope="function")],
) -> APIResponse[dict[str, int]]:
    service = get_notification_service(db)

    updated_count = await service.mark_all_notifications_as_read(
        current_user=current_user
    )
    return APIResponse(
        message="All notifications marked as read successfully",
        data={"updated_count": updated_count},
    )


@router.delete(
    "",
    response_model=MessageResponse,
    responses={
        **UNAUTHORIZED_RESPONSE,
        **VALIDATION_ERROR_RESPONSE,
    },
)
async def delete_read_notifications(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db, scope="function")],
    status: Literal["read"] = "read",
) -> MessageResponse:
    service = get_notification_service(db)

    await service.delete_all_read_notifications(
        current_user=current_user,
    )

    return MessageResponse(
        message="Read notifications deleted successfully",
    )


@router.delete(
    "/{id}",
    response_model=MessageResponse,
    responses={**UNAUTHORIZED_RESPONSE, **VALIDATION_ERROR_RESPONSE},
)
async def delete_notification(
    id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db, scope="function")],
) -> MessageResponse:
    service = get_notification_service(db)

    await service.delete_notification(current_user=current_user, notification_id=id)

    return MessageResponse(
        message="Notification deleted successfully",
    )
