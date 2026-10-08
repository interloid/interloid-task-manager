from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.enums.email_otp import EmailOtpPurpose
from app.mail.dependencies import get_mailer
from app.mail.fake import FakeMailer
from app.main import app
from app.models.email_otp import EmailOtp
from app.models.user import User


async def test_forgot_password_existing_user_sends_reset_otp(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    fake_mailer = FakeMailer()

    app.dependency_overrides[get_mailer] = lambda: fake_mailer

    try:
        register_response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "forgot-password@example.com",
                "password": "password123",
                "first_name": "Amal",
                "last_name": "Das",
            },
        )

        assert register_response.status_code == 201
        assert len(fake_mailer.sent_emails) == 1

        fake_mailer.sent_emails.clear()

        response = await client.post(
            "/api/v1/auth/forgot-password",
            json={
                "email": "forgot-password@example.com",
            },
        )

        assert response.status_code == 200

        body = response.json()

        assert body["success"] is True
        assert body["message"] == (
            "If an account exists for this email, a password reset code has been sent."
        )

        assert len(fake_mailer.sent_emails) == 1

        email = fake_mailer.sent_emails[0]

        assert email["to_email"] == "forgot-password@example.com"
        assert email["subject"] == "Reset your password"

        user_result = await db_session.execute(
            select(User).where(
                User.email == "forgot-password@example.com",
            )
        )

        user = user_result.scalar_one()

        otp_result = await db_session.execute(
            select(EmailOtp).where(
                EmailOtp.user_id == user.id,
                EmailOtp.purpose == EmailOtpPurpose.RESET_PASSWORD,
            )
        )

        reset_otp = otp_result.scalar_one()

        assert len(reset_otp.otp_hash) == 64
        assert reset_otp.failed_attempts == 0
        assert reset_otp.used_at is None
        assert reset_otp.invalidated_at is None

    finally:
        app.dependency_overrides.pop(
            get_mailer,
            None,
        )


async def test_forgot_password_unknown_email_returns_200(
    client: AsyncClient,
) -> None:
    fake_mailer = FakeMailer()

    app.dependency_overrides[get_mailer] = lambda: fake_mailer

    try:
        response = await client.post(
            "/api/v1/auth/forgot-password",
            json={
                "email": "unknown-forgot@example.com",
            },
        )

        assert response.status_code == 200

        body = response.json()

        assert body["success"] is True
        assert body["message"] == (
            "If an account exists for this email, a password reset code has been sent."
        )
        assert len(fake_mailer.sent_emails) == 0

    finally:
        app.dependency_overrides.pop(
            get_mailer,
            None,
        )


async def test_forgot_password_invalidates_previous_reset_otp(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    fake_mailer = FakeMailer()
    app.dependency_overrides[get_mailer] = lambda: fake_mailer

    try:
        register_response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "forgot-twice@example.com",
                "password": "password123",
                "first_name": "Amal",
                "last_name": "Das",
            },
        )

        assert register_response.status_code == 201

        fake_mailer.sent_emails.clear()

        first_response = await client.post(
            "/api/v1/auth/forgot-password",
            json={
                "email": "forgot-twice@example.com",
            },
        )

        assert first_response.status_code == 200
        assert len(fake_mailer.sent_emails) == 1

        user_result = await db_session.execute(
            select(User).where(
                User.email == "forgot-twice@example.com",
            )
        )
        user = user_result.scalar_one()

        first_otp_result = await db_session.execute(
            select(EmailOtp).where(
                EmailOtp.user_id == user.id,
                EmailOtp.purpose == EmailOtpPurpose.RESET_PASSWORD,
            )
        )
        first_otp = first_otp_result.scalar_one()

        assert first_otp.invalidated_at is None

        first_otp.created_at = (
            datetime.now(UTC)
            - timedelta(
                seconds=settings.PASSWORD_RESET_OTP_RESEND_COOLDOWN_SECONDS + 1,
            )
        )

        await db_session.commit()

        

        second_response = await client.post(
            "/api/v1/auth/forgot-password",
            json={
                "email": "forgot-twice@example.com",
            },
        )

        assert second_response.status_code == 200
        assert len(fake_mailer.sent_emails) == 2

        await db_session.refresh(first_otp)

        assert first_otp.invalidated_at is not None

        otp_result = await db_session.execute(
            select(EmailOtp)
            .where(
                EmailOtp.user_id == user.id,
                EmailOtp.purpose == EmailOtpPurpose.RESET_PASSWORD,
            )
            .order_by(EmailOtp.created_at.asc())
            .execution_options(
                populate_existing=True,
            )
        )

        reset_otps = otp_result.scalars().all()

        assert len(reset_otps) == 2

        old_otp = reset_otps[0]
        new_otp = reset_otps[1]

        assert old_otp.invalidated_at is not None
        assert new_otp.invalidated_at is None
        assert new_otp.used_at is None
        assert new_otp.failed_attempts == 0

    finally:
        app.dependency_overrides.pop(
            get_mailer,
            None,
        )

    
