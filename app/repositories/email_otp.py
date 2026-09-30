from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums.email_otp import EmailOtpPurpose
from app.models.email_otp import EmailOtp


class EmailOtpRepository:
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.session = session

    async def create(
        self,
        email_otp: EmailOtp,
    ) -> EmailOtp:
        self.session.add(email_otp)

        await self.session.flush()
        await self.session.refresh(email_otp)

        return email_otp

    async def get_active_for_update(
        self,
        *,
        user_id: UUID,
        purpose: EmailOtpPurpose,
    ) -> EmailOtp | None:
        result = await self.session.execute(
            select(EmailOtp)
            .where(
                EmailOtp.user_id == user_id,
                EmailOtp.purpose == purpose,
                EmailOtp.used_at.is_(None),
                EmailOtp.invalidated_at.is_(None),
                EmailOtp.expires_at > datetime.now(UTC),
            )
            .order_by(
                EmailOtp.created_at.desc(),
            )
            .with_for_update()
        )

        return result.scalars().first()

    async def increment_failed_attempts(
        self,
        email_otp: EmailOtp,
    ) -> None:
        email_otp.failed_attempts += 1

        await self.session.flush()

    async def mark_used(
        self,
        email_otp: EmailOtp,
    ) -> None:
        email_otp.used_at = datetime.now(UTC)

        await self.session.flush()

    async def invalidate(
        self,
        email_otp: EmailOtp,
    ) -> None:
        email_otp.invalidated_at = datetime.now(UTC)

        await self.session.flush()

    async def get_latest_for_update(
        self,
        *,
        user_id: UUID,
        purpose: EmailOtpPurpose,
    ) -> EmailOtp | None:
        result = await self.session.execute(
            select(EmailOtp)
            .where(
                EmailOtp.user_id == user_id,
                EmailOtp.purpose == purpose,
            )
            .order_by(
                EmailOtp.created_at.desc(),
            )
            .with_for_update()
        )

        return result.scalars().first()

    async def invalidate_active(
        self,
        *,
        user_id: UUID,
        purpose: EmailOtpPurpose,
    ) -> None:
        now = datetime.now(UTC)

        result = await self.session.execute(
            select(EmailOtp)
            .where(
                EmailOtp.user_id == user_id,
                EmailOtp.purpose == purpose,
                EmailOtp.used_at.is_(None),
                EmailOtp.invalidated_at.is_(None),
            )
            .with_for_update()
        )

        email_otps = result.scalars().all()

        for email_otp in email_otps:
            email_otp.invalidated_at = now

        await self.session.flush()
