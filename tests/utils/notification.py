from sqlalchemy.ext.asyncio import AsyncSession

from app.enums.notification import NotificationStatus, NotificationType
from app.models.notification import Notification
from app.models.user import User


async def create_notification(
    db_session: AsyncSession,
    user: User,
    status: NotificationStatus = NotificationStatus.UNREAD,
) -> Notification:
    notification = Notification(
        user_id=user.id,
        task_id=None,
        type=NotificationType.TASK_COMMENTED,
        title="New comment",
        message="A new comment was added to your task.",
        status=status,
    )

    db_session.add(notification)
    await db_session.commit()
    await db_session.refresh(notification)

    return notification
