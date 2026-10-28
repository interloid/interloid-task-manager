from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TaskCommentCreateRequest(BaseModel):
    content: str = Field(
        min_length=1,
        max_length=5000,
    )

    @field_validator("content", mode="before")
    @classmethod
    def validate_content_not_null(cls, value: object) -> object:
        if value is None:
            raise ValueError("content cannot be null")

        return value

    @field_validator("content")
    @classmethod
    def validate_content_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("content cannot be empty or whitespace")

        return value


class TaskCommentUpdateRequest(BaseModel):
    content: str = Field(
        min_length=1,
        max_length=5000,
    )

    @field_validator("content", mode="before")
    @classmethod
    def validate_content_not_null(cls, value: object) -> object:
        if value is None:
            raise ValueError("content cannot be null")

        return value

    @field_validator("content")
    @classmethod
    def validate_content_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("content cannot be empty or whitespace")

        return value


class TaskCommentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    task_id: UUID
    user_id: UUID
    content: str
    created_at: datetime
    updated_at: datetime
