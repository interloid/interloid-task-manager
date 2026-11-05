import json
from uuid import UUID

from redis.asyncio import Redis

from app.models.notification import Notification


class NotificationPublisher:
    def __init__(self, redis: Redis) -> None:
        self.redis = redis

    @staticmethod
    def get_channel(user_id: UUID) -> str:
        return f"notifications:{user_id}"

    async def publish(self, notification: Notification) -> None:
        event = {
            "id": str(notification.id),
            "type": notification.type.value,
            "title": notification.title,
            "message": notification.message,
            "task_id": (
                str(notification.task_id) if notification.task_id is not None else None
            ),
            "status": notification.status.value,
            "created_at": notification.created_at.isoformat(),
        }

        await self.redis.publish(
            self.get_channel(notification.user_id),
            json.dumps(event),
        )
