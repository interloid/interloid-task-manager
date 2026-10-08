from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.api.responses import (
    FORBIDDEN_RESPONSE,
    NOT_FOUND_RESPONSE,
    UNAUTHORIZED_RESPONSE,
    VALIDATION_ERROR_RESPONSE,
)
from app.db.dependencies import get_db
from app.models.user import User
from app.repositories.refresh_token import RefreshTokenRepository
from app.repositories.user import UserRepository
from app.schemas import APIResponse, PaginatedResponse, UserResponse, UserUpdateRequest
from app.services.user import UserService

router = APIRouter(
    prefix="/users",
    tags=["User Administration"],
)


@router.get(
    "",
    response_model=PaginatedResponse[UserResponse],
    status_code=status.HTTP_200_OK,
    responses={
        **UNAUTHORIZED_RESPONSE,
        **FORBIDDEN_RESPONSE,
        **VALIDATION_ERROR_RESPONSE,
    },
)
async def list_users(
    page: int = Query(
        default=1,
        ge=1,
    ),
    page_size: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
    _: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db, scope="function"),
) -> PaginatedResponse[UserResponse]:
    user_repository = UserRepository(session)
    refresh_token_repository = RefreshTokenRepository(session)

    service = UserService(
        user_repository=user_repository,
        refresh_token_repository=refresh_token_repository,
    )

    return await service.list_users(
        page=page,
        page_size=page_size,
    )


@router.patch(
    "/{id}",
    response_model=APIResponse[UserResponse],
    status_code=status.HTTP_200_OK,
    responses={
        **UNAUTHORIZED_RESPONSE,
        **FORBIDDEN_RESPONSE,
        **NOT_FOUND_RESPONSE,
        **VALIDATION_ERROR_RESPONSE,
    },
)
async def update_user(
    id: UUID,
    request: UserUpdateRequest,
    current_admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db, scope="function"),
) -> APIResponse[UserResponse]:
    user_repository = UserRepository(session)
    refresh_token_repository = RefreshTokenRepository(session)

    service = UserService(
        user_repository=user_repository, 
        refresh_token_repository=refresh_token_repository, 
    )

    user = await service.update_user(
        id=id,
        request=request,
        current_admin=current_admin,
    )

    return APIResponse(
        message="User updated successfully",
        data=user,
    )
