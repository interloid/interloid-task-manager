import os
from functools import cached_property
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL

ENV_FILE = os.getenv("ENV_FILE", ".env")


class Settings(BaseSettings):
    APP_NAME: str
    APP_VERSION: str

    HOST: str
    PORT: int

    DEBUG: bool
    LOG_LEVEL: str

    DB_HOST: str
    DB_PORT: int
    DB_NAME: str
    DB_USER: str
    DB_PASSWORD: SecretStr
    DB_SSL: bool

    REDIS_URL: str
    REDIS_KEY_PREFIX: str

    SECRET_KEY: SecretStr

    FRONTEND_URL: str = "http://localhost:5173"

    COOKIE_SECURE: bool = False
    COOKIE_SAMESITE: Literal["lax", "strict", "none"] = "lax"

    AWS_REGION: str = "ap-southeast-1"
    S3_BUCKET_NAME: str

    AWS_ACCESS_KEY_ID: SecretStr | None = None
    AWS_SECRET_ACCESS_KEY: SecretStr | None = None

    S3_PRESIGNED_URL_EXPIRE_SECONDS: int = Field(
        default=300,
        ge=60,
        le=3600,
    )

    TASK_ATTACHMENT_MAX_SIZE_BYTES: int = Field(
        default=10 * 1024 * 1024,
        ge=1,
    )

    EMAIL_OTP_EXPIRE_MINUTES: int = Field(
        default=5,
        ge=1,
        le=30,
    )

    EMAIL_OTP_MAX_ATTEMPTS: int = Field(
        default=5,
        ge=1,
        le=10,
    )

    EMAIL_OTP_RESEND_COOLDOWN_SECONDS: int = Field(
        default=60,
        ge=1,
        le=300,
    )

    PASSWORD_RESET_OTP_RESEND_COOLDOWN_SECONDS: int = Field(
        default=60,
        ge=1,
        le=300,
    )

    SMTP_HOST: str
    SMTP_PORT: int = 587

    SMTP_USERNAME: str
    SMTP_PASSWORD: SecretStr

    SMTP_FROM_EMAIL: str
    SMTP_FROM_NAME: str = "Interloid Task Manager"
    SMTP_USE_TLS: bool = True

    OTP_SECRET_KEY: SecretStr

    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: SecretStr
    GOOGLE_REDIRECT_URI: str

    JWT_SECRET_KEY: SecretStr
    JWT_ALGORITHM: Literal["HS256", "HS384", "HS512"] = "HS256"

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def validate_jwt_secret(
        cls,
        value: SecretStr,
    ) -> SecretStr:
        secret = value.get_secret_value()

        if len(secret.encode("utf-8")) < 32:
            raise ValueError("JWT_SECRET_KEY must be at least 32 bytes long")

        return value

    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=60,
        ge=1,
        le=1440,
    )

    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(
        default=7,
        ge=1,
        le=90,
    )

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @cached_property
    def database_url(self) -> str:
        url = URL.create(
            drivername="postgresql+asyncpg",
            username=self.DB_USER,
            password=self.DB_PASSWORD.get_secret_value(),
            host=self.DB_HOST,
            port=self.DB_PORT,
            database=self.DB_NAME,
        )

        return url.render_as_string(
            hide_password=False,
        )


settings = Settings()
