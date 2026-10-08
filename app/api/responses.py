from typing import Any

from fastapi import status

from app.schemas.common import ErrorResponse

type OpenAPIResponses = dict[int | str, dict[str, Any]]


UNAUTHORIZED_RESPONSE: OpenAPIResponses = {
    status.HTTP_401_UNAUTHORIZED: {
        "model": ErrorResponse,
        "description": "Authentication required or token is invalid",
    },
}


INVALID_CREDENTIALS_RESPONSE: OpenAPIResponses = {
    status.HTTP_401_UNAUTHORIZED: {
        "model": ErrorResponse,
        "description": "Invalid email or password",
    },
}


INVALID_REFRESH_TOKEN_RESPONSE: OpenAPIResponses = {
    status.HTTP_401_UNAUTHORIZED: {
        "model": ErrorResponse,
        "description": "Invalid or expired refresh token",
    },
}


INVALID_CURRENT_PASSWORD_RESPONSE: OpenAPIResponses = {
    status.HTTP_401_UNAUTHORIZED: {
        "model": ErrorResponse,
        "description": "Authentication failed or current password is incorrect",
    },
}


INVALID_EMAIL_OTP_RESPONSE: OpenAPIResponses = {
    status.HTTP_400_BAD_REQUEST: {
        "model": ErrorResponse,
        "description": "Invalid or expired verification code",
    },
}


EMAIL_ALREADY_VERIFIED_RESPONSE: OpenAPIResponses = {
    status.HTTP_409_CONFLICT: {
        "model": ErrorResponse,
        "description": "Email is already verified",
    },
}


EMAIL_ALREADY_EXISTS_RESPONSE: OpenAPIResponses = {
    status.HTTP_409_CONFLICT: {
        "model": ErrorResponse,
        "description": "Email already exists",
    },
}


FORBIDDEN_RESPONSE: OpenAPIResponses = {
    status.HTTP_403_FORBIDDEN: {
        "model": ErrorResponse,
        "description": "Permission denied",
    },
}


NOT_FOUND_RESPONSE: OpenAPIResponses = {
    status.HTTP_404_NOT_FOUND: {
        "model": ErrorResponse,
        "description": "Resource not found",
    },
}


VALIDATION_ERROR_RESPONSE: OpenAPIResponses = {
    status.HTTP_422_UNPROCESSABLE_CONTENT: {
        "model": ErrorResponse,
        "description": "Validation error",
    },
}

TOO_MANY_REQUESTS_RESPONSE: OpenAPIResponses= {
    status.HTTP_429_TOO_MANY_REQUESTS: {
        "model": ErrorResponse,
        "description": "Too many requests",
    }
}
