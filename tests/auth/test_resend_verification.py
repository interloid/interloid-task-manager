import re
from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.mail.dependencies import get_mailer
from app.mail.fake import FakeMailer
from app.main import app
from app.models.email_otp import EmailOtp
from app.models.user import User


async def test_resend_verification_success(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    fake_mailer = FakeMailer()

    app.dependency_overrides[get_mailer] = lambda: fake_mailer

    try:
        register_response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "resend@example.com",
                "password": "password123",
                "first_name": "Amal",
                "last_name": "Das",
            },
        )

        assert register_response.status_code == 201
        assert len(fake_mailer.sent_emails) == 1

        user_result = await db_session.execute(
            select(User).where(
                User.email == "resend@example.com",
            )
        )

        user = user_result.scalar_one()

        otp_result = await db_session.execute(
            select(EmailOtp).where(
                EmailOtp.user_id == user.id,
            )
        )

        first_otp = otp_result.scalar_one()

        first_otp.created_at = datetime.now(UTC) - timedelta(seconds=61)

        await db_session.commit()

        response = await client.post(
            "/api/v1/auth/resend-verification",
            json={
                "email": "resend@example.com",
            },
        )

        assert response.status_code == 200

        await db_session.refresh(first_otp)

        body = response.json()

        assert body["success"] is True
        assert (
            body["message"]
            == "If an account exists for this email, a verification code has been sent."
        )

        assert len(fake_mailer.sent_emails) == 2

        otp_result = await db_session.execute(
            select(EmailOtp)
            .where(
                EmailOtp.user_id == user.id,
            )
            .order_by(
                EmailOtp.created_at.asc(),
            )
        )

        email_otps = otp_result.scalars().all()

        assert len(email_otps) == 2

        old_otp = email_otps[0]
        new_otp = email_otps[1]

        assert old_otp.invalidated_at is not None
        assert new_otp.invalidated_at is None
        assert new_otp.used_at is None
        assert new_otp.failed_attempts == 0

    finally:
        app.dependency_overrides.pop(
            get_mailer,
            None,
        )


async def test_resend_verification_within_cooldown_returns_429(
    client: AsyncClient,
) -> None:
    fake_mailer = FakeMailer()

    app.dependency_overrides[get_mailer] = lambda: fake_mailer

    try:
        register_response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "cooldown@example.com",
                "password": "password123",
                "first_name": "Amal",
                "last_name": "Das",
            },
        )

        assert register_response.status_code == 201
        assert len(fake_mailer.sent_emails) == 1

        response = await client.post(
            "/api/v1/auth/resend-verification",
            json={
                "email": "cooldown@example.com",
            },
        )

        assert response.status_code == 429

        body = response.json()

        assert body["success"] is False
        assert body["error"]["code"] == "EMAIL_OTP_RESEND_COOLDOWN"

        assert "Retry-After" in response.headers

        retry_after = int(response.headers["Retry-After"])

        assert 1 <= retry_after <= 60

        assert len(fake_mailer.sent_emails) == 1

    finally:
        app.dependency_overrides.pop(
            get_mailer,
            None,
        )


async def test_resend_verification_already_verified_returns_409(
    client: AsyncClient,
) -> None:
    fake_mailer = FakeMailer()

    app.dependency_overrides[get_mailer] = lambda: fake_mailer

    try:
        register_response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "verified-resend@example.com",
                "password": "password123",
                "first_name": "Amal",
                "last_name": "Das",
            },
        )

        assert register_response.status_code == 201
        assert len(fake_mailer.sent_emails) == 1

        email = fake_mailer.sent_emails[0]

        match = re.search(
            r"\b\d{6}\b",
            email["text_body"],
        )

        assert match is not None

        otp = match.group()

        verify_response = await client.post(
            "/api/v1/auth/verify-email",
            json={
                "email": "verified-resend@example.com",
                "otp": otp,
            },
        )

        assert verify_response.status_code == 200

        resend_response = await client.post(
            "/api/v1/auth/resend-verification",
            json={
                "email": "verified-resend@example.com",
            },
        )

        assert resend_response.status_code == 409

        body = resend_response.json()

        assert body["success"] is False
        assert body["error"]["code"] == "EMAIL_ALREADY_VERIFIED"

        assert len(fake_mailer.sent_emails) == 1

    finally:
        app.dependency_overrides.pop(
            get_mailer,
            None,
        )


async def test_resend_verification_unknown_email_returns_200(
    client: AsyncClient,
) -> None:
    fake_mailer = FakeMailer()

    app.dependency_overrides[get_mailer] = lambda: fake_mailer

    try:
        response = await client.post(
            "/api/v1/auth/resend-verification",
            json={
                "email": "unknown-resend@example.com",
            },
        )

        assert response.status_code == 200

        body = response.json()

        assert body["success"] is True
        assert (
            body["message"]
            == "If an account exists for this email, a verification code has been sent."
        )

        assert len(fake_mailer.sent_emails) == 0

    finally:
        app.dependency_overrides.pop(
            get_mailer,
            None,
        )
