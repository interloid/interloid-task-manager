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


async def test_verify_email_success(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    fake_mailer = FakeMailer()

    app.dependency_overrides[get_mailer] = lambda: fake_mailer

    try:
        register_response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "verify-success@example.com",
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
                "email": "verify-success@example.com",
                "otp": otp,
            },
        )

        assert verify_response.status_code == 200

        body = verify_response.json()

        assert body["success"] is True
        assert body["message"] == "Email verified successfully"

        user_result = await db_session.execute(
            select(User).where(
                User.email == "verify-success@example.com",
            )
        )

        user = user_result.scalar_one()

        assert user.is_verified is True

        otp_result = await db_session.execute(
            select(EmailOtp).where(
                EmailOtp.user_id == user.id,
            )
        )

        email_otp = otp_result.scalar_one()

        assert email_otp.used_at is not None

    finally:
        app.dependency_overrides.pop(
            get_mailer,
            None,
        )


async def test_verify_email_wrong_otp_returns_400(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    fake_mailer = FakeMailer()

    app.dependency_overrides[get_mailer] = lambda: fake_mailer

    try:
        register_response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "wrong-otp@example.com",
                "password": "password123",
                "first_name": "Amal",
                "last_name": "Das",
            },
        )

        assert register_response.status_code == 201

        verify_response = await client.post(
            "/api/v1/auth/verify-email",
            json={
                "email": "wrong-otp@example.com",
                "otp": "111111",
            },
        )

        assert verify_response.status_code == 400

        body = verify_response.json()

        assert body["success"] is False
        assert body["error"]["code"] == "INVALID_EMAIL_OTP"

        user_result = await db_session.execute(
            select(User).where(
                User.email == "wrong-otp@example.com",
            )
        )

        user = user_result.scalar_one()

        assert user.is_verified is False

        otp_result = await db_session.execute(
            select(EmailOtp).where(
                EmailOtp.user_id == user.id,
            )
        )

        email_otp = otp_result.scalar_one()

        assert email_otp.failed_attempts == 1
        assert email_otp.used_at is None

    finally:
        app.dependency_overrides.pop(
            get_mailer,
            None,
        )


async def test_verify_email_fifth_wrong_attempt_invalidates_otp(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    fake_mailer = FakeMailer()

    app.dependency_overrides[get_mailer] = lambda: fake_mailer

    try:
        register_response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "max-attempts@example.com",
                "password": "password123",
                "first_name": "Amal",
                "last_name": "Das",
            },
        )

        assert register_response.status_code == 201

        for _ in range(4):
            response = await client.post(
                "/api/v1/auth/verify-email",
                json={
                    "email": "max-attempts@example.com",
                    "otp": "111111",
                },
            )

            assert response.status_code == 400
            assert response.json()["error"]["code"] == "INVALID_EMAIL_OTP"

        response = await client.post(
            "/api/v1/auth/verify-email",
            json={
                "email": "max-attempts@example.com",
                "otp": "111111",
            },
        )

        assert response.status_code == 429

        body = response.json()

        assert body["success"] is False
        assert body["error"]["code"] == "EMAIL_OTP_ATTEMPTS_EXCEEDED"

        user_result = await db_session.execute(
            select(User).where(
                User.email == "max-attempts@example.com",
            )
        )

        user = user_result.scalar_one()

        otp_result = await db_session.execute(
            select(EmailOtp).where(
                EmailOtp.user_id == user.id,
            )
        )

        email_otp = otp_result.scalar_one()

        assert email_otp.failed_attempts == 5
        assert email_otp.invalidated_at is not None
        assert email_otp.used_at is None
        assert user.is_verified is False

    finally:
        app.dependency_overrides.pop(
            get_mailer,
            None,
        )


async def test_verify_email_expired_otp_returns_400(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    fake_mailer = FakeMailer()

    app.dependency_overrides[get_mailer] = lambda: fake_mailer

    try:
        register_response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "expired-otp@example.com",
                "password": "password123",
                "first_name": "Amal",
                "last_name": "Das",
            },
        )

        assert register_response.status_code == 201

        email = fake_mailer.sent_emails[0]

        match = re.search(
            r"\b\d{6}\b",
            email["text_body"],
        )

        assert match is not None

        otp = match.group()

        user_result = await db_session.execute(
            select(User).where(
                User.email == "expired-otp@example.com",
            )
        )

        user = user_result.scalar_one()

        otp_result = await db_session.execute(
            select(EmailOtp).where(
                EmailOtp.user_id == user.id,
            )
        )

        email_otp = otp_result.scalar_one()

        email_otp.expires_at = datetime.now(UTC) - timedelta(minutes=1)

        await db_session.commit()

        response = await client.post(
            "/api/v1/auth/verify-email",
            json={
                "email": "expired-otp@example.com",
                "otp": otp,
            },
        )

        assert response.status_code == 400

        body = response.json()

        assert body["success"] is False
        assert body["error"]["code"] == "INVALID_EMAIL_OTP"

    finally:
        app.dependency_overrides.pop(
            get_mailer,
            None,
        )


async def test_verify_email_already_verified_returns_409(
    client: AsyncClient,
) -> None:
    fake_mailer = FakeMailer()

    app.dependency_overrides[get_mailer] = lambda: fake_mailer

    try:
        register_response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "already-verified@example.com",
                "password": "password123",
                "first_name": "Amal",
                "last_name": "Das",
            },
        )

        assert register_response.status_code == 201

        email = fake_mailer.sent_emails[0]

        match = re.search(
            r"\b\d{6}\b",
            email["text_body"],
        )

        assert match is not None

        otp = match.group()

        first_response = await client.post(
            "/api/v1/auth/verify-email",
            json={
                "email": "already-verified@example.com",
                "otp": otp,
            },
        )

        assert first_response.status_code == 200

        second_response = await client.post(
            "/api/v1/auth/verify-email",
            json={
                "email": "already-verified@example.com",
                "otp": otp,
            },
        )

        assert second_response.status_code == 409

        body = second_response.json()

        assert body["success"] is False
        assert body["error"]["code"] == "EMAIL_ALREADY_VERIFIED"

    finally:
        app.dependency_overrides.pop(
            get_mailer,
            None,
        )


async def test_verify_email_unknown_email_returns_400(
    client: AsyncClient,
) -> None:
    response = await client.post(
        "/api/v1/auth/verify-email",
        json={
            "email": "unknown@example.com",
            "otp": "123456",
        },
    )

    assert response.status_code == 400

    body = response.json()

    assert body["success"] is False
    assert body["error"]["code"] == "INVALID_EMAIL_OTP"
