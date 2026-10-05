from uuid import UUID

from app.enums import RoleName
from app.exceptions.user import (
    LastActiveAdminException,
    SelfModificationNotAllowedException,
    UserNotFoundException,
)
from app.models.user import User
from app.repositories.refresh_token import RefreshTokenRepository
from app.repositories.user import UserRepository
from app.schemas import (
    PaginatedResponse,
    PaginationMeta,
    UserResponse,
    UserUpdateRequest,
)


class UserService:
    def __init__(
            self, 
            user_repository: UserRepository,
            refresh_token_repository: RefreshTokenRepository,
    ) -> None:
        self.user_repository = user_repository
        self.refresh_token_repository = refresh_token_repository

    async def list_users(
        self,
        page: int,
        page_size: int,
    ) -> PaginatedResponse[UserResponse]:
        offset = (page - 1) * page_size

        users, total = await self.user_repository.list_users(
            limit=page_size,
            offset=offset,
        )

        total_pages = (total + page_size - 1) // page_size

        data = [UserResponse.model_validate(user) for user in users]

        return PaginatedResponse(
            message="Users retrieved successfully",
            data=data,
            pagination=PaginationMeta(
                page=page,
                page_size=page_size,
                total=total,
                total_pages=total_pages,
            ),
        )

    async def update_user(
        self,
        id: UUID,
        request: UserUpdateRequest,
        current_admin: User,
    ) -> UserResponse:
        user = await self.user_repository.get_by_id_for_update(id)

        if user is None:
            raise UserNotFoundException()

        if user.id == current_admin.id:
            if request.role is not None and request.role != current_admin.role:
                raise SelfModificationNotAllowedException()

            if request.is_active is not None and request.is_active is False:
                raise SelfModificationNotAllowedException()

        target_is_active_admin = user.role == RoleName.ADMIN and user.is_active

        removes_admin_access = request.is_active is False or (
            request.role is not None and request.role != RoleName.ADMIN
        )

        if target_is_active_admin and removes_admin_access:
            active_admins = await self.user_repository.get_active_admins_for_update()

            if len(active_admins) <= 1:
                raise LastActiveAdminException()

        user = await self.user_repository.update_user(
            user=user,
            role=request.role,
            is_active=request.is_active,
        )

        if request.is_active is False:
            await self.refresh_token_repository.revoke_all_for_user(
                user.id,
        )

        return UserResponse.model_validate(user)
