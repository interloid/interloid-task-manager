from app.exceptions.base import AppException


class NotificationNotFoundException(AppException):
    def __init__(self) -> None:
        super().__init__(
            message="Notification not found",
            code="NOTIFICATION_NOT_FOUND",
            status_code=404,
        )
