from fastapi import status

from app.exceptions.base import AppException


class InvalidAttachmentException(AppException):
    def __init__(
        self,
        message: str = "Invalid attachment",
        code: str = "INVALID_ATTACHMENT",
    ) -> None:
        super().__init__(
            message=message,
            code=code,
            status_code=status.HTTP_400_BAD_REQUEST,
        )


class UnsupportedAttachmentTypeException(AppException):
    def __init__(self) -> None:
        super().__init__(
            message="This file type is not supported",
            code="UNSUPPORTED_FILE_TYPE",
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        )


class AttachmentTooLargeException(AppException):
    def __init__(self) -> None:
        super().__init__(
            message="File exceeds the maximum allowed size",
            code="FILE_TOO_LARGE",
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        )


class AttachmentNotFoundException(AppException):
    def __init__(self) -> None:
        super().__init__(
            message="Attachment not found",
            code="ATTACHMENT_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
        )
