import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from uuid6 import uuid7

from app.core.config import settings
from app.core.rate_limit import login_rate_limiter
from app.core.security import (
    DUMMY_PASSWORD_HASH,
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.exceptions.auth import (
    EmailAlreadyExistsException,
    EmailNotVerifiedException,
    InvalidCredentialsException,
    InvalidCurrentPasswordException,
    InvalidRefreshTokenException,
    LoginRateLimitExceededException,
    SamePasswordException,
    SessionNotFoundException,
    UnauthorizedException,
)
from app.mail.base import Mailer
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.repositories.refresh_token import RefreshTokenRepository
from app.repositories.user import UserRepository
from app.schemas import (
    ChangePasswordRequest,
    CollectionResponse,
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    SessionResponse,
    UserResponse,
)
from app.services.email_verification import EmailVerificationService
from app.utils.user_agent import parse_user_agent

logger = logging.getLogger(__name__)


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.user_repository = UserRepository(session)
        self.refresh_token_repository = RefreshTokenRepository(session)

    async def register(
        self,
        request: RegisterRequest,
        mailer: Mailer,
    ) -> UserResponse:
        if await self.user_repository.email_exists(request.email):
            raise EmailAlreadyExistsException()

        hashed_password = hash_password(request.password)

        user = User(
            email=request.email,
            password_hash=hashed_password,
            first_name=request.first_name,
            last_name=request.last_name,
            is_verified=False,
        )

        try:
            async with self.session.begin_nested():
                user = await self.user_repository.create(user)
        except IntegrityError as exc:
            raise EmailAlreadyExistsException() from exc

        email_verification_service = EmailVerificationService(
            self.session,
        )

        await email_verification_service.send_verification_otp(user, mailer)

        return UserResponse.model_validate(user)

    async def login(
        self,
        request: LoginRequest,
        user_agent: str | None = None,
        client_ip: str = "unknown",
    ) -> LoginResponse:
        retry_after = await login_rate_limiter.get_retry_after(
            client_ip=client_ip,
            email=request.email,
        )

        if retry_after is not None:
            raise LoginRateLimitExceededException(
                retry_after=retry_after,
            )

        user = await self.user_repository.get_by_email_for_update(request.email)

        password_hash = user.password_hash if user is not None else DUMMY_PASSWORD_HASH

        password_ok = verify_password(request.password, password_hash)

        if user is None or not password_ok or not user.is_active:
            await login_rate_limiter.record_failure(
                client_ip=client_ip,
                email=request.email,
            )

            raise InvalidCredentialsException()

        if not user.is_verified: 
            raise EmailNotVerifiedException()

        browser, os_name = parse_user_agent(
            user_agent,
        )

        family_id = uuid7()

        access_token = create_access_token(
            subject=str(user.id),
            session_id=str(family_id),
        )

        refresh_token = create_refresh_token()

        refresh_token_hash = hash_refresh_token(refresh_token)

        refresh_token_record = RefreshToken(
            token_hash=refresh_token_hash,
            expires_at=datetime.now(UTC)
            + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
            user_id=user.id,
            browser=browser,
            os=os_name,
            family_id=family_id,
        )
        await self.refresh_token_repository.create(
            refresh_token_record,
        )

        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
        )

    async def refresh_access_token(
        self,
        refresh_token: str,
    ) -> LoginResponse:
        refresh_token_hash = hash_refresh_token(refresh_token)

        stored_token = await self.refresh_token_repository.get_by_token_hash_for_update(
            refresh_token_hash
        )
        if stored_token is None:
            raise InvalidRefreshTokenException()

        if (
            stored_token.revoked_at is not None
            and stored_token.replaced_by_id is not None
        ):
            await self.refresh_token_repository.revoke_family(
                stored_token.family_id,
            )

            await self.session.commit()

            logger.warning(
                "Refresh token replay detected: user_id=%s family_id=%s",
                stored_token.user_id,
                stored_token.family_id,
            )

            raise InvalidRefreshTokenException()

        if stored_token.revoked_at is not None:
            raise InvalidRefreshTokenException()

        if stored_token.expires_at <= datetime.now(UTC):
            raise InvalidRefreshTokenException()

        user = await self.user_repository.get_by_id(
            stored_token.user_id,
        )

        if user is None or not user.is_active:
            raise InvalidRefreshTokenException()

        new_refresh_token = create_refresh_token()

        new_refresh_token_hash = hash_refresh_token(
            new_refresh_token,
        )

        new_refresh_token_record = RefreshToken(
            token_hash=new_refresh_token_hash,
            expires_at=(
                datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
            ),
            user_id=user.id,
            browser=stored_token.browser,
            os=stored_token.os,
            family_id=stored_token.family_id,
        )

        new_refresh_token_record = await self.refresh_token_repository.create(
            new_refresh_token_record,
        )

        await self.refresh_token_repository.mark_as_rotated(
            stored_token,
            new_refresh_token_record.id,
        )

        access_token = create_access_token(
            subject=str(user.id),
            session_id=str(stored_token.family_id),
        )

        return LoginResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
        )

    async def logout(
        self,
        refresh_token: str,
    ) -> None:
        refresh_token_hash = hash_refresh_token(refresh_token)

        stored_token = await self.refresh_token_repository.get_by_token_hash_for_update(
            refresh_token_hash,
        )

        if stored_token is None:
            raise InvalidRefreshTokenException()

        if stored_token.revoked_at is not None:
            return

        await self.refresh_token_repository.revoke(
            stored_token,
        )

    async def change_password(
        self,
        user: User,
        request: ChangePasswordRequest,
    ) -> None:
        locked_user = await self.user_repository.get_by_id_for_update(
            user.id,
        )

        if locked_user is None:
            raise UnauthorizedException()

        if not verify_password(
            request.current_password,
            locked_user.password_hash,
        ):
            raise InvalidCurrentPasswordException()

        if verify_password(
            request.new_password,
            locked_user.password_hash,
        ):
            raise SamePasswordException()

        new_password_hash = hash_password(
            request.new_password,
        )

        await self.user_repository.update_password(
            locked_user,
            new_password_hash,
        )

        await self.refresh_token_repository.revoke_all_for_user(
            locked_user.id,
        )

    async def get_sessions(
        self,
        *,
        user: User,
        current_session_id: UUID,
    ) -> CollectionResponse[SessionResponse]:
        sessions = await self.refresh_token_repository.get_active_sessions_for_user(
            user.id,
        )

        items = [
            SessionResponse(
                id=session.family_id,
                browser=session.browser,
                os=session.os,
                created_at=session.created_at,
                expires_at=session.expires_at,
                is_current=(session.family_id == current_session_id),
            )
            for session in sessions
        ]

        return CollectionResponse(
            message="Active sessions fetched successfully",
            data=items,
            total=len(items),
        )

    async def revoke_session(self, *, user: User, family_id: UUID) -> None:
        session = await self.refresh_token_repository.get_active_session_by_family_id(
            user_id=user.id,
            family_id=family_id,
        )

        if session is None:
            raise SessionNotFoundException()

        await self.refresh_token_repository.revoke_family(
            family_id,
        )

    async def logout_all(
        self,
        user: User,
    ) -> None:
        await self.refresh_token_repository.revoke_all_for_user(
            user.id,
        )
