from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TaskAttachmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    task_id: UUID
    uploaded_by_id: UUID
    original_filename: str
    content_type: str
    file_size: int
    created_at: datetime
    updated_at: datetime


class AttachmentDownloadResponse(BaseModel):
    download_url: str
    expires_in: int = Field(description="Presigned URL lifetime in seconds")
