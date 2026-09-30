from app.exceptions.base import AppException


class UserNotFoundException(AppException):
    def __init__(self) -> None:
        super().__init__(
            message="User not found",
            code="USER_NOT_FOUND",
            status_code=404,
        )


class SelfModificationNotAllowedException(AppException):
    def __init__(self) -> None:
        super().__init__(
            message="Admins cannot deactivate or demote themselves",
            code="SELF_MODIFICATION_NOT_ALLOWED",
            status_code=422,
        )


class LastActiveAdminException(AppException):
    def __init__(self) -> None:
        super().__init__(
            message="The last active admin cannot be demoted or deactivated",
            code="LAST_ACTIVE_ADMIN",
            status_code=422,
        )
