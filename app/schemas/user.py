from pydantic import BaseModel

from app.enums import RoleName

# from app.schemas.common import PaginationMeta


# class UserListResponse(BaseModel):
#     items: list[UserResponse]
#     pagination: PaginationMeta


class UserUpdateRequest(BaseModel):
    role: RoleName | None = None
    is_active: bool | None = None
