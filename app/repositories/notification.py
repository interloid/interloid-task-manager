from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import NotificationStatus
from app.models import Notification


class NotificationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        notification: Notification,
    ) -> Notification:
        self.session.add(notification)
        await self.session.flush()
        await self.session.refresh(notification)
        return notification

    async def get_by_user_id(
        self,
        *,
        user_id: UUID,
        limit: int,
        offset: int,
        is_read: bool | None = None,
    ) -> tuple[list[Notification], int]:
        conditions = [Notification.user_id == user_id]

        if is_read is not None:
            status = NotificationStatus.READ if is_read else NotificationStatus.UNREAD
            conditions.append(Notification.status == status)

        count_statement = (
            select(func.count()).select_from(Notification).where(*conditions)
        )

        total = await self.session.scalar(count_statement) or 0

        statement = (
            select(Notification)
            .where(*conditions)
            .order_by(
                Notification.created_at.desc(),
                Notification.id.desc(),
            )
            .limit(limit)
            .offset(offset)
        )

        result = await self.session.scalars(statement)
        notifications = list(result.all())

        return notifications, total

    async def get_by_id_and_user_id(
        self,
        *,
        notification_id: UUID,
        user_id: UUID,
    ) -> Notification | None:
        statement = select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user_id,
        )

        result = await self.session.scalar(statement)

        return result

    async def get_unread_count(
        self,
        *,
        user_id: UUID,
    ) -> int:
        statement = (
            select(func.count())
            .select_from(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.status == NotificationStatus.UNREAD,
            )
        )

        result = await self.session.scalar(statement)

        return result or 0

    async def mark_all_as_read(
        self,
        *,
        user_id: UUID,
    ) -> int:
        statement = (
            update(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.status == NotificationStatus.UNREAD,
            )
            .values(status=NotificationStatus.READ)
            .returning(Notification.id)
        )

        result = await self.session.scalars(statement)
        updated_ids = result.all()

        return len(updated_ids)

    async def delete(
        self,
        notification: Notification,
    ) -> None:
        await self.session.delete(notification)
        await self.session.flush()

    async def delete_all_read(
        self,
        *,
        user_id: UUID,
    ) -> None:
        statement = delete(Notification).where(
            Notification.user_id == user_id,
            Notification.status == NotificationStatus.READ,
        )

        await self.session.execute(statement)
