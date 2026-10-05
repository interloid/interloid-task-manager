from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.responses import (
    INVALID_EMAIL_OTP_RESPONSE,
    TOO_MANY_REQUESTS_RESPONSE,
    VALIDATION_ERROR_RESPONSE,
)
from app.db.dependencies import get_db
from app.mail.base import Mailer
from app.mail.dependencies import get_mailer
from app.schemas import ForgotPasswordRequest, MessageResponse, ResetPasswordRequest
from app.services.email_verification import EmailVerificationService

router = APIRouter(prefix="/auth", tags=["Password Recovery"])


@router.post(
    "/forgot-password",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    responses={
        **VALIDATION_ERROR_RESPONSE,
        **TOO_MANY_REQUESTS_RESPONSE,
    },
)
async def forgot_password(
    request: ForgotPasswordRequest,
    mailer: Annotated[Mailer, Depends(get_mailer)],
    session: Annotated[AsyncSession, Depends(get_db, scope="function")],
) -> MessageResponse:
    service = EmailVerificationService(session)

    await service.forgot_password(
        email=str(request.email),
        mailer=mailer,
    )

    return MessageResponse(
        message=(
            "If an account exists for this email, a password reset code has been sent."
        ),
    )


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    responses={
        **VALIDATION_ERROR_RESPONSE,
        **INVALID_EMAIL_OTP_RESPONSE,
    },
)
async def reset_password(
    request: ResetPasswordRequest,
    session: Annotated[
        AsyncSession,
        Depends(get_db, scope="function"),
    ],
) -> MessageResponse:
    service = EmailVerificationService(
        session,
    )

    await service.reset_password(
        email=str(request.email),
        otp=request.otp,
        new_password=request.new_password,
    )

    return MessageResponse(
        message="Password reset successfully",
    )
