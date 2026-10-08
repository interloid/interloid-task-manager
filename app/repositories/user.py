from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums.role import RoleName
from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, User)

    async def get_by_email(
        self,
        email: str,
    ) -> User | None:
        result = await self.session.execute(
            select(User).where(User.email == email),
        )

        return result.scalar_one_or_none()

    async def get_by_email_for_update(
        self,
        email: str,
    ) -> User | None:
        result = await self.session.execute(
            select(User)
            .where(
                User.email == email,
            )
            .with_for_update()
            .execution_options(
                populate_existing=True,
            )
        )

        return result.scalar_one_or_none()

    async def get_by_id_for_update(
        self,
        id: UUID,
    ) -> User | None:
        result = await self.session.execute(
            select(User)
            .where(
                User.id == id,
            )
            .with_for_update()
            .execution_options(
                populate_existing=True,
            )
        )

        return result.scalar_one_or_none()

    async def email_exists(
        self,
        email: str,
    ) -> bool:
        return await self.get_by_email(email) is not None

    async def update_password(
        self,
        user: User,
        password_hash: str,
    ) -> User:
        user.password_hash = password_hash
        user.password_changed_at = datetime.now(UTC)

        await self.session.flush()
        await self.session.refresh(user)

        return user

    async def list_users(
        self,
        limit: int,
        offset: int,
    ) -> tuple[list[User], int]:
        total_result = await self.session.execute(
            select(func.count()).select_from(User),
        )
        total = total_result.scalar_one()

        result = await self.session.execute(
            select(User)
            .order_by(
                User.created_at.desc(),
                User.id.desc(),
            )
            .limit(limit)
            .offset(offset),
        )

        users = list(result.scalars().all())

        return users, total

    async def update_user(
        self,
        user: User,
        role: RoleName | None = None,
        is_active: bool | None = None,
    ) -> User:
        if role is not None:
            user.role = role

        if is_active is not None:
            user.is_active = is_active

        await self.session.flush()
        await self.session.refresh(user)

        return user

    async def get_active_admins_for_update(
        self,
    ) -> list[User]:
        result = await self.session.execute(
            select(User)
            .where(
                User.role == RoleName.ADMIN,
                User.is_active.is_(True),
            )
            .with_for_update()
        )

        return list(result.scalars().all())

    async def mark_email_verified(
        self,
        user: User,
    ) -> None:
        user.is_verified = True

        await self.session.flush()
