from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.responses import (
    INVALID_CURRENT_PASSWORD_RESPONSE,
    UNAUTHORIZED_RESPONSE,
    VALIDATION_ERROR_RESPONSE,
)
from app.db.dependencies import get_db
from app.models.user import User
from app.schemas import (
    APIResponse,
    ChangePasswordRequest,
    MessageResponse,
    UserResponse,
)
from app.services.auth import AuthService

router = APIRouter(
    prefix="/users",
    tags=["User Profile"],
)


@router.get(
    "/me",
    response_model=APIResponse[UserResponse],
    status_code=status.HTTP_200_OK,
    responses={
        **UNAUTHORIZED_RESPONSE,
    },
)
async def get_me(
    current_user: User = Depends(get_current_user),
) -> APIResponse[UserResponse]:
    user = UserResponse.model_validate(current_user)
    return APIResponse(
        message="Current user retrieved successfully",
        data=user,
    )


@router.patch(
    "/me/password",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    responses={
        **INVALID_CURRENT_PASSWORD_RESPONSE,
        **VALIDATION_ERROR_RESPONSE,
    },
)
async def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db, scope="function"),
) -> MessageResponse:
    service = AuthService(session)
    await service.change_password(
        current_user,
        request,
    )

    return MessageResponse(
        message="password changed successfully",
    )
