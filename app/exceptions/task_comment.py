from fastapi import status

from app.exceptions.base import AppException


class TaskCommentNotFoundException(AppException):
    def __init__(self) -> None:
        super().__init__(
            message="Task comment not found",
            code="TASK_COMMENT_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
        )
