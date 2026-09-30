from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ErrorDetail(BaseModel):
    code: str
    details: Any | None = None


class PaginationMeta(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int


class PaginatedResponse(BaseModel, Generic[T]):
    success: Literal[True] = True
    message: str
    data: list[T]
    pagination: PaginationMeta


class APIResponse(BaseModel, Generic[T]):
    success: Literal[True] = True
    message: str
    data: T


class MessageResponse(BaseModel):
    success: Literal[True] = True
    message: str


class ErrorResponse(BaseModel):
    success: Literal[False] = False
    message: str
    error: ErrorDetail
