from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.enums.task import SortOrder, TaskPriority, TaskSortBy, TaskStatus


class TaskCreateRequest(BaseModel):
    title: str = Field(
        min_length=1,
        max_length=200,
    )
    description: str | None = None
    status: TaskStatus = TaskStatus.TODO
    priority: TaskPriority = TaskPriority.MEDIUM
    due_date: date | None = None

    @field_validator("title", mode="before")
    @classmethod
    def validate_title_not_null(cls, value: object) -> object:
        if value is None:
            raise ValueError("title cannot be null")

        return value


class TaskUpdateRequest(BaseModel):
    title: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
    )
    description: str | None = None
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    due_date: date | None = None

    @model_validator(mode="after")
    def validate_non_nullable_fields(self) -> "TaskUpdateRequest":
        non_nullable_fields = (
            "title",
            "status",
            "priority",
        )

        for field in non_nullable_fields:
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")

        return self


class TaskResponse(BaseModel):
    id: UUID
    owner_id: UUID
    title: str
    description: str | None
    status: TaskStatus
    priority: TaskPriority
    due_date: date | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TaskListQuery(BaseModel):
    owner_id: UUID | None = None

    status: TaskStatus | None = None
    priority: TaskPriority | None = None

    due_from: date | None = None
    due_to: date | None = None

    search: str | None = None

    page: int = Field(
        default=1,
        ge=1,
    )

    page_size: int = Field(
        default=20,
        ge=1,
        le=100,
    )

    sort_by: TaskSortBy = TaskSortBy.CREATED_AT
    order: SortOrder = SortOrder.DESC

    @model_validator(mode="after")
    def validate_due_date_range(self) -> "TaskListQuery":
        if (
            self.due_from is not None
            and self.due_to is not None
            and self.due_from > self.due_to
        ):
            raise ValueError("due_from must be less than or equal to due_to")

        return self
