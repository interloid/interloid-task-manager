from pydantic import BaseModel

from app.enums import RoleName


class UserUpdateRequest(BaseModel):
    role: RoleName | None = None
    is_active: bool | None = None
