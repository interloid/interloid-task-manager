import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from pwdlib import PasswordHash
from uuid6 import uuid7

from app.core.config import settings
from app.enums.token import TokenType

password_hash = PasswordHash.recommended()

DUMMY_PASSWORD_HASH = password_hash.hash(
    secrets.token_urlsafe(32),
)


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:
    return password_hash.verify(
        plain_password,
        hashed_password,
    )


def create_access_token(
    subject: str,
    session_id: str,
) -> str:
    now = datetime.now(UTC)
    expires_at = now + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
    )

    payload: dict[str, Any] = {
        "sub": subject,
        "exp": expires_at,
        "iat": now.timestamp(),
        "jti": str(uuid7()),
        "iss": settings.APP_NAME,
        "type": TokenType.ACCESS.value,
        "sid": session_id,
    }

    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY.get_secret_value(),
        algorithm=settings.JWT_ALGORITHM,
    )


def create_refresh_token() -> str:
    return secrets.token_urlsafe(64)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(
        token.encode("utf-8"),
    ).hexdigest()


def decode_token(token: str) -> dict[str, Any]:
    return jwt.decode(
        token,
        settings.JWT_SECRET_KEY.get_secret_value(),
        algorithms=[settings.JWT_ALGORITHM],
        issuer=settings.APP_NAME,
        options={
            "require": [
                "sub",
                "exp",
                "iat",
                "jti",
                "iss",
                "type",
                "sid",
            ],
        },
    )
