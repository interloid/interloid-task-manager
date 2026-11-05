from fastapi import status

from app.exceptions.base import AppException


class NotificationNotFoundException(AppException):
    def __init__(self) -> None:
        super().__init__(
            message="Notification not found",
            code="NOTIFICATION_NOT_FOUND",
            status_code=404,
        )


class SSEConnectionLimitExceededException(AppException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            message=(
                "Maximum SSE connections reached. "
                "Close an existing connection and try again."
            ),
            code="SSE_CONNECTION_LIMIT_EXCEEDED",
        )
