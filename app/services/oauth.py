from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from uuid6 import uuid7

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_refresh_token,
)
from app.enums import RoleName
from app.exceptions.auth import (
    OAuthAccountConflictException,
    UnauthorizedException,
)
from app.models.oauth_account import OAuthAccount
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.repositories.oauth_account import OAuthAccountRepository
from app.repositories.refresh_token import RefreshTokenRepository
from app.repositories.user import UserRepository
from app.schemas import LoginResponse
from app.utils.user_agent import parse_user_agent


class OAuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.user_repository = UserRepository(session)
        self.oauth_account_repository = OAuthAccountRepository(session)
        self.refresh_token_repository = RefreshTokenRepository(session)

    async def login(
        self,
        *,
        provider: str,
        claims: Mapping[str, Any],
        user_agent: str | None = None,
    ) -> LoginResponse:
        provider_user_id = claims.get("sub")
        email = claims.get("email")
        email_verified = claims.get("email_verified")

        if isinstance(email, str):
            email = email.strip().lower()

        if (
            not isinstance(provider_user_id, str)
            or not provider_user_id
            or not isinstance(email, str)
            or not email
            or email_verified is not True
        ):
            raise UnauthorizedException()

        oauth_account = await self.oauth_account_repository.get_by_provider_user_id(
            provider,
            provider_user_id,
        )

        if oauth_account is not None:
            user = await self.user_repository.get_by_id(
                oauth_account.user_id,
            )

            if user is None or not user.is_active:
                raise UnauthorizedException()

        else:
            existing_user = await self.user_repository.get_by_email(email)

            if existing_user is not None:
                raise OAuthAccountConflictException()

            given_name = claims.get("given_name")
            family_name = claims.get("family_name")
            full_name = claims.get("name")

            if not isinstance(given_name, str) or not given_name.strip():
                given_name = (
                    full_name.strip()
                    if isinstance(full_name, str) and full_name.strip()
                    else email.split("@", maxsplit=1)[0]
                )

            if not isinstance(family_name, str):
                family_name = ""

            user = User(
                email=email,
                password_hash=None,
                first_name=given_name.strip()[:100],
                last_name=family_name.strip()[:100],
                role=RoleName.USER,
                is_active=True,
                is_verified=True,
            )

            try:
                async with self.session.begin_nested():
                    user = await self.user_repository.create(user)
                    oauth_account = OAuthAccount(
                        user_id=user.id,
                        provider=provider,
                        provider_user_id=provider_user_id,
                        email=email,
                    )
                    await self.oauth_account_repository.create(oauth_account)

            except IntegrityError as exc:
                raise OAuthAccountConflictException() from exc

        browser, os_name = parse_user_agent(user_agent)
        family_id = uuid7()

        access_token = create_access_token(
            subject=str(user.id),
            session_id=str(family_id),
        )

        refresh_token = create_refresh_token()

        refresh_token_record = RefreshToken(
            token_hash=hash_refresh_token(refresh_token),
            expires_at=(
                datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
            ),
            user_id=user.id,
            browser=browser,
            os=os_name,
            family_id=family_id,
        )

        await self.refresh_token_repository.create(refresh_token_record)

        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
        )
