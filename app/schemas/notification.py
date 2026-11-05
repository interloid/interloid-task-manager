from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.enums.notification import NotificationStatus, NotificationType


class NotificationCreateRequest(BaseModel):
    task_id: UUID | None = None
    type: NotificationType
    title: str = Field(min_length=1, max_length=200)
    message: str = Field(min_length=1)


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    task_id: UUID | None
    type: NotificationType
    title: str
    message: str
    status: NotificationStatus
    created_at: datetime
    updated_at: datetime


class NotificationListQuery(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    is_read: bool | None = None
