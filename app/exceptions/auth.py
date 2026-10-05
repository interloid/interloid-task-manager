from fastapi import status

from app.exceptions.base import AppException


class EmailAlreadyExistsException(AppException):
    def __init__(self) -> None:
        super().__init__(
            message="Email already exists",
            code="EMAIL_ALREADY_EXISTS",
            status_code=409,
        )


class InvalidCredentialsException(AppException):
    def __init__(self) -> None:
        super().__init__(
            message="Invalid email or password",
            code="INVALID_CREDENTIALS",
            status_code=401,
        )


class InvalidRefreshTokenException(AppException):
    def __init__(self) -> None:
        super().__init__(
            message="Invalid or expired refresh token",
            code="INVALID_REFRESH_TOKEN",
            status_code=401,
        )


class UnauthorizedException(AppException):
    def __init__(self) -> None:
        super().__init__(
            message="Invalid or missing authentication credentials",
            code="UNAUTHORIZED",
            status_code=401,
            headers={
                "WWW-Authenticate": "Bearer",
            },
        )


class InvalidCurrentPasswordException(AppException):
    def __init__(self) -> None:
        super().__init__(
            message="Current password is incorrect",
            code="INVALID_CURRENT_PASSWORD",
            status_code=401,
        )


class ForbiddenException(AppException):
    def __init__(
        self,
        message: str = "You do not have permission to perform this action",
        code: str = "FORBIDDEN",
    ) -> None:
        super().__init__(
            message=message,
            code=code,
            status_code=403,
        )


class SamePasswordException(AppException):
    def __init__(self) -> None:
        super().__init__(
            message="New password must be different from the current password",
            code="SAME_PASSWORD",
            status_code=422,
        )


class PasswordReuseNotAllowedException(AppException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            message="New password must be different from the current password",
            code="PASSWORD_REUSE_NOT_ALLOWED",
        )


class LoginRateLimitExceededException(AppException):
    def __init__(
        self,
        retry_after: int,
    ) -> None:
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            message="Too many login attempts",
            code="LOGIN_RATE_LIMIT_EXCEEDED",
            headers={
                "Retry-After": str(retry_after),
            },
        )

class PasswordResetRateLimitExceededException(AppException):
    def __init__(
        self,
        retry_after: int,
    ) -> None:
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            message="Too many password reset requests",
            code="PASSWORD_RESET_RATE_LIMIT_EXCEEDED",
            headers={
                "Retry-After": str(retry_after),
            },
        )

class SessionNotFoundException(AppException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Session not found",
            code="SESSION_NOT_FOUND",
        )


class InvalidEmailOtpException(AppException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Invalid or expired verification code",
            code="INVALID_EMAIL_OTP",
        )


class EmailOtpAttemptsExceededException(AppException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            message="Maximum OTP attempts exceeded. Request a new code.",
            code="EMAIL_OTP_ATTEMPTS_EXCEEDED",
        )


class EmailOtpResendCooldownException(AppException):
    def __init__(
        self,
        retry_after: int,
    ) -> None:
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            message="Please wait before requesting another verification code",
            code="EMAIL_OTP_RESEND_COOLDOWN",
            headers={
                "Retry-After": str(retry_after),
            },
        )

class PasswordResetCooldownException(AppException):
    def __init__(
        self,
        retry_after: int,
    ) -> None:
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            message="Please wait before requesting another password reset code",
            code="PASSWORD_RESET_COOLDOWN",
            headers={
                "Retry-After": str(retry_after),
            },
        )


class EmailAlreadyVerifiedException(AppException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            message="Email is already verified",
            code="EMAIL_ALREADY_VERIFIED",
        )


class EmailNotVerifiedException(AppException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            message="Email verification is required before login",
            code="EMAIL_NOT_VERIFIED",
        )
