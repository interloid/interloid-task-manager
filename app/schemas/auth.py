import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.enums import RoleName


def validate_password_strength(value: str) -> str:
    if not re.search(r"[A-Za-z]", value):
        raise ValueError(
            "password must contain at least one letter",
        )
    if not re.search(r"\d", value):
        raise ValueError(
            "password must contain at least one number",
        )
    return value


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(
        min_length=8,
        max_length=128,
    )
    first_name: str = Field(
        min_length=1,
        max_length=100,
    )
    last_name: str = Field(
        min_length=1,
        max_length=100,
    )

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return validate_password_strength(value)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    first_name: str
    last_name: str
    role: RoleName
    is_active: bool
    is_verified: bool
    created_at: datetime


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(
        min_length=8,
        max_length=128,
    )


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str = Field(
        min_length=1,
        max_length=256,
    )


class LogoutRequest(BaseModel):
    refresh_token: str = Field(
        min_length=1,
        max_length=256,
    )


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(
        min_length=1,
        max_length=128,
    )
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        return validate_password_strength(value)


class SessionResponse(BaseModel):
    id: UUID
    browser: str | None
    os: str | None
    created_at: datetime
    expires_at: datetime
    is_current: bool


class SessionListResponse(BaseModel):
    items: list[SessionResponse]
    total: int


class VerifyEmailRequest(BaseModel):
    email: EmailStr

    otp: str = Field(
        min_length=6,
        max_length=6,
        pattern=r"^\d{6}$",
    )


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    email: EmailStr

    otp: str = Field(
        min_length=6,
        max_length=6,
        pattern=r"^\d{6}$",
    )

    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        return validate_password_strength(value)
