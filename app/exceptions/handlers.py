import logging
from typing import Any

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.exceptions.base import AppException

logger = logging.getLogger(__name__)


def build_error_content(
    *,
    message: str,
    code: str,
    details: Any | None = None,
) -> dict[str, Any]:
    error: dict[str, Any] = {
        "code": code,
    }

    if details is not None:
        error["details"] = details

    return {
        "success": False,
        "message": message,
        "error": error,
    }


async def app_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    if not isinstance(exc, AppException):
        return await generic_exception_handler(
            request,
            exc,
        )

    return JSONResponse(
        status_code=exc.status_code,
        headers=exc.headers,
        content=build_error_content(
            message=exc.message,
            code=exc.code,
            details=exc.details,
        ),
    )


async def validation_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    if not isinstance(exc, RequestValidationError):
        return await generic_exception_handler(request, exc)

    details: dict[str, list[str]] = {}

    for error in exc.errors():
        location = error.get("loc", [])

        field = str(location[-1]) if location else "request"

        message = str(error.get("msg", "Invalid value"))

        details.setdefault(field, []).append(message)

    return JSONResponse(
        status_code=422,
        content=build_error_content(
            message="Validation failed",
            code="VALIDATION_ERROR",
            details=details,
        ),
    )


async def generic_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    logger.exception(
        "Unhandled exception",
        exc_info=exc,
    )

    return JSONResponse(
        status_code=500,
        content=build_error_content(
            message="Internal server error",
            code="INTERNAL_SERVER_ERROR",
        ),
    )


async def http_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    if not isinstance(exc, HTTPException):
        return await generic_exception_handler(request, exc)

    code_by_status = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        409: "CONFLICT",
        422: "VALIDATION_ERROR",
        429: "TOO_MANY_REQUESTS",
    }

    return JSONResponse(
        status_code=exc.status_code,
        headers=exc.headers,
        content=build_error_content(
            message=str(exc.detail),
            code=code_by_status.get(
                exc.status_code,
                "HTTP_ERROR",
            ),
        ),
    )
