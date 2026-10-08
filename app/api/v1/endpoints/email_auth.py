from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.responses import (
    EMAIL_ALREADY_VERIFIED_RESPONSE,
    INVALID_EMAIL_OTP_RESPONSE,
    TOO_MANY_REQUESTS_RESPONSE,
    VALIDATION_ERROR_RESPONSE,
)
from app.db.dependencies import get_db
from app.mail.base import Mailer
from app.mail.dependencies import get_mailer
from app.schemas import (
    MessageResponse,
    ResendVerificationRequest,
    VerifyEmailRequest,
)
from app.services.email_verification import EmailVerificationService

router = APIRouter(prefix="/auth", tags=["Email Authentication"])


@router.post(
    "/verify-email",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    responses={
        **INVALID_EMAIL_OTP_RESPONSE,
        **EMAIL_ALREADY_VERIFIED_RESPONSE,
        **VALIDATION_ERROR_RESPONSE,   
    },
)
async def verify_email(
    request: VerifyEmailRequest,
    session: Annotated[
        AsyncSession,
        Depends(get_db, scope="function"),
    ],
) -> MessageResponse:
    service = EmailVerificationService(
        session,
    )
    await service.verify_email(
        email=str(request.email),
        otp=request.otp,
    )

    return MessageResponse(
        message="Email verified successfully",
    )


@router.post(
    "/resend-verification",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    responses={
        **VALIDATION_ERROR_RESPONSE,
        **EMAIL_ALREADY_VERIFIED_RESPONSE,
        **TOO_MANY_REQUESTS_RESPONSE,
    },
)
async def resend_verification(
    request: ResendVerificationRequest,
    mailer: Annotated[
        Mailer,
        Depends(get_mailer),
    ],
    session: Annotated[
        AsyncSession,
        Depends(get_db, scope="function"),
    ],
) -> MessageResponse:
    service = EmailVerificationService(
        session,
    )

    await service.resend_verification_otp(
        email=str(request.email),
        mailer=mailer,
    )

    return MessageResponse(
        message=(
            "If an account exists for this email, a verification code has been sent."
        ),
    )
