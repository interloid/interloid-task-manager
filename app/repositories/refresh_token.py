from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.refresh_token import RefreshToken
from app.repositories.base import BaseRepository


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, RefreshToken)

    async def get_by_token_hash_for_update(
        self,
        token_hash: str,
    ) -> RefreshToken | None:
        result = await self.session.execute(
            select(RefreshToken)
            .where(
                RefreshToken.token_hash == token_hash,
            )
            .with_for_update()
        )

        return result.scalar_one_or_none()

    async def revoke(
        self,
        refresh_token: RefreshToken,
    ) -> None:
        refresh_token.revoked_at = datetime.now(UTC)
        await self.session.flush()

    async def revoke_all_for_user(
        self,
        id: UUID,
    ) -> None:
        await self.session.execute(
            update(RefreshToken)
            .where(
                RefreshToken.user_id == id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(
                revoked_at=datetime.now(UTC),
            )
        )

        await self.session.flush()

    async def get_active_sessions_for_user(
        self,
        user_id: UUID,
    ) -> list[RefreshToken]:
        result = await self.session.execute(
            select(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
                RefreshToken.expires_at > datetime.now(UTC),
            )
            .order_by(
                RefreshToken.created_at.desc(),
                RefreshToken.id.desc(),
            )
        )

        return list(result.scalars().all())

    async def get_active_session_by_family_id(
        self,
        *,
        user_id: UUID,
        family_id: UUID,
    ) -> RefreshToken | None:
        result = await self.session.execute(
            select(RefreshToken).where(
                RefreshToken.user_id == user_id,
                RefreshToken.family_id == family_id,
                RefreshToken.revoked_at.is_(None),
                RefreshToken.expires_at > datetime.now(UTC),
            )
        )

        return result.scalar_one_or_none()

    async def revoke_family(
        self,
        family_id: UUID,
    ) -> None:
        await self.session.execute(
            update(RefreshToken)
            .where(
                RefreshToken.family_id == family_id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(
                revoked_at=datetime.now(UTC),
            )
        )

        await self.session.flush()

    async def mark_as_rotated(
        self,
        refresh_token: RefreshToken,
        replaced_by_id: UUID,
    ) -> None:
        refresh_token.revoked_at = datetime.now(UTC)
        refresh_token.replaced_by_id = replaced_by_id

        await self.session.flush()
