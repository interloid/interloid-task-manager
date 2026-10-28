from uuid import UUID

from app.enums import NotificationStatus, NotificationType
from app.exceptions.notification import NotificationNotFoundException
from app.exceptions.task import TaskNotFoundException
from app.models.notification import Notification
from app.models.user import User
from app.repositories import NotificationRepository, TaskRepository
from app.schemas import (
    NotificationListQuery,
    NotificationResponse,
    PaginatedResponse,
    PaginationMeta,
)


class NotificationService:
    def __init__(
        self,
        *,
        notification_repository: NotificationRepository,
        task_repository: TaskRepository,
    ) -> None:
        self.notification_repository = notification_repository
        self.task_repository = task_repository

    async def create_notification(
        self,
        *,
        recipient_id: UUID,
        task_id: UUID | None,
        notification_type: NotificationType,
        title: str,
        message: str,
    ) -> Notification:
        if task_id is not None:
            task = await self.task_repository.get_by_id(task_id)

            if task is None:
                raise TaskNotFoundException()

        notification = Notification(
            user_id=recipient_id,
            task_id=task_id,
            type=notification_type,
            title=title,
            message=message,
        )

        return await self.notification_repository.create(
            notification=notification,
        )

    async def get_user_notifications(
        self,
        *,
        current_user: User,
        query: NotificationListQuery,
    ) -> PaginatedResponse[NotificationResponse]:
        offset = (query.page - 1) * query.page_size

        notifications, total = await self.notification_repository.get_by_user_id(
            user_id=current_user.id,
            limit=query.page_size,
            offset=offset,
            is_read=query.is_read,
        )

        total_pages = (total + query.page_size - 1) // query.page_size

        data = [
            NotificationResponse.model_validate(notification)
            for notification in notifications
        ]

        return PaginatedResponse(
            message="Notifications retrieved successfully",
            data=data,
            pagination=PaginationMeta(
                page=query.page,
                page_size=query.page_size,
                total=total,
                total_pages=total_pages,
            ),
        )

    async def mark_notification_as_read(
        self,
        *,
        current_user: User,
        notification_id: UUID,
    ) -> Notification:
        notification = await self.notification_repository.get_by_id_and_user_id(
            notification_id=notification_id,
            user_id=current_user.id,
        )

        if notification is None:
            raise NotificationNotFoundException()

        notification.status = NotificationStatus.READ

        return notification

    async def get_unread_notification_count(
        self,
        *,
        current_user: User,
    ) -> int:
        return await self.notification_repository.get_unread_count(
            user_id=current_user.id,
        )

    async def mark_all_notifications_as_read(
        self,
        *,
        current_user: User,
    ) -> int:
        return await self.notification_repository.mark_all_as_read(
            user_id=current_user.id,
        )

    async def delete_notification(
        self,
        *,
        current_user: User,
        notification_id: UUID,
    ) -> None:
        notification = await self.notification_repository.get_by_id_and_user_id(
            notification_id=notification_id,
            user_id=current_user.id,
        )

        if notification is None:
            raise NotificationNotFoundException()

        await self.notification_repository.delete(notification)

    async def delete_all_read_notifications(
        self,
        current_user: User,
    ) -> None:
        await self.notification_repository.delete_all_read(
            user_id=current_user.id,
        )
