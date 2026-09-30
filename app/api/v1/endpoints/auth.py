from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.responses import (
    EMAIL_ALREADY_EXISTS_RESPONSE,
    INVALID_CREDENTIALS_RESPONSE,
    INVALID_REFRESH_TOKEN_RESPONSE,
    VALIDATION_ERROR_RESPONSE,
)
from app.db.dependencies import get_db
from app.mail.base import Mailer
from app.mail.dependencies import get_mailer
from app.schemas import (
    APIResponse,
    LoginRequest,
    LoginResponse,
    MessageResponse,
    RefreshRequest,
    RegisterRequest,
    UserResponse,
)
from app.services.auth import AuthService

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


@router.post(
    "/register",
    response_model=APIResponse[UserResponse],
    status_code=status.HTTP_201_CREATED,
    responses={
        **EMAIL_ALREADY_EXISTS_RESPONSE,
        **VALIDATION_ERROR_RESPONSE,
    },
)
async def register(
    request: RegisterRequest,
    mailer: Annotated[Mailer, Depends(get_mailer)],
    session: AsyncSession = Depends(get_db, scope="function"),
) -> APIResponse[UserResponse]:
    service = AuthService(
        session,
    )

    user = await service.register(request, mailer)

    return APIResponse(
        message=("User registered successfully. Verification code sent to email."),
        data=user,
    )


@router.post(
    "/login",
    response_model=APIResponse[LoginResponse],
    status_code=status.HTTP_200_OK,
    responses={
        **INVALID_CREDENTIALS_RESPONSE,
        **VALIDATION_ERROR_RESPONSE,
    },
)
async def login(
    request: LoginRequest,
    http_request: Request,
    session: AsyncSession = Depends(get_db, scope="function"),
) -> APIResponse[LoginResponse]:
    service = AuthService(session)

    user_agent = http_request.headers.get(
        "user-agent",
    )

    client_ip = (
        http_request.client.host if http_request.client is not None else "unknown"
    )

    tokens = await service.login(
        request,
        user_agent=user_agent,
        client_ip=client_ip,
    )

    return APIResponse(
        message="Login successful",
        data=tokens,
    )


@router.post(
    "/refresh",
    response_model=APIResponse[LoginResponse],
    status_code=status.HTTP_200_OK,
    responses={
        **INVALID_REFRESH_TOKEN_RESPONSE,
        **VALIDATION_ERROR_RESPONSE,
    },
)
async def refresh_token(
    request: RefreshRequest,
    session: AsyncSession = Depends(get_db, scope="function"),
) -> APIResponse[LoginResponse]:
    service = AuthService(session)

    tokens = await service.refresh_access_token(request.refresh_token)

    return APIResponse(
        message="Access token refreshed successfully",
        data=tokens,
    )


@router.post(
    "/logout",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    responses={
        **VALIDATION_ERROR_RESPONSE,
    },
)
async def logout(
    request: RefreshRequest,
    session: AsyncSession = Depends(get_db, scope="function"),
) -> MessageResponse:
    service = AuthService(session)

    await service.logout(
        request.refresh_token,
    )

    return MessageResponse(
        message="Logged out successfully",
    )
