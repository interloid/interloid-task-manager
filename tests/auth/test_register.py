from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums.email_otp import EmailOtpPurpose
from app.mail.dependencies import get_mailer
from app.mail.fake import FakeMailer
from app.main import app
from app.models.email_otp import EmailOtp
from app.models.user import User


async def test_register_user(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "testuser@example.com",
            "password": "StrongPassword123!",
            "first_name": "Test",
            "last_name": "User",
        },
    )

    assert response.status_code == 201

    body = response.json()

    assert body["success"] is True
    assert body["data"]["email"] == "testuser@example.com"
    assert body["data"]["first_name"] == "Test"
    assert body["data"]["last_name"] == "User"
    assert body["data"]["role"] == "user"
    assert body["data"]["is_active"] is True

    result = await db_session.execute(
        select(User).where(
            User.email == "testuser@example.com",
        )
    )

    user = result.scalar_one_or_none()

    assert user is not None
    assert user.email == "testuser@example.com"
    assert user.first_name == "Test"
    assert user.last_name == "User"
    assert user.role.value == "user"
    assert user.is_active is True


async def test_register_duplicate_email_returns_409(
    client: AsyncClient,
) -> None:
    payload = {
        "email": "duplicate@example.com",
        "password": "StrongPassword123!",
        "first_name": "Test",
        "last_name": "User",
    }

    first_response = await client.post(
        "/api/v1/auth/register",
        json=payload,
    )

    second_response = await client.post(
        "/api/v1/auth/register",
        json=payload,
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409


async def test_register_invalid_email_returns_422(
    client: AsyncClient,
) -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "invalid-email",
            "password": "StrongPassword123!",
            "first_name": "Test",
            "last_name": "User",
        },
    )

    assert response.status_code == 422


async def test_register_missing_email_returns_422(
    client: AsyncClient,
) -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "password": "StrongPassword123!",
            "first_name": "Test",
            "last_name": "User",
        },
    )

    assert response.status_code == 422


async def test_register_missing_password_returns_422(
    client: AsyncClient,
) -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "testuser@example.com",
            "first_name": "Test",
            "last_name": "User",
        },
    )

    assert response.status_code == 422


async def test_register_weak_password_returns_422(
    client: AsyncClient,
) -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "testuser@example.com",
            "password": "123",
            "first_name": "Test",
            "last_name": "User",
        },
    )

    assert response.status_code == 422


async def test_login_inactive_user_returns_401(
    client: AsyncClient,
    inactive_user,
) -> None:
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": inactive_user.email,
            "password": "StrongPassword123!",
        },
    )

    assert response.status_code == 401

    body = response.json()

    assert body["success"] is False
    assert body["error"]["code"] == "INVALID_CREDENTIALS"


async def test_register_sends_verification_email(
    client: AsyncClient,
) -> None:
    fake_mailer = FakeMailer()

    app.dependency_overrides[get_mailer] = lambda: fake_mailer

    try:
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "verify@example.com",
                "password": "password123",
                "first_name": "Amal",
                "last_name": "Das",
            },
        )

        assert response.status_code == 201

        body = response.json()

        assert body["success"] is True
        assert body["data"]["email"] == "verify@example.com"

        assert len(fake_mailer.sent_emails) == 1

        email = fake_mailer.sent_emails[0]

        assert email["to_email"] == "verify@example.com"
        assert email["subject"] == "Verify your email"

        assert "Amal" in email["html_body"]
        assert "verification code" in email["html_body"]

    finally:
        app.dependency_overrides.pop(
            get_mailer,
            None,
        )


async def test_register_stores_hashed_verification_otp(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    fake_mailer = FakeMailer()

    app.dependency_overrides[get_mailer] = lambda: fake_mailer

    try:
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "otp-hash@example.com",
                "password": "password123",
                "first_name": "Amal",
                "last_name": "Das",
            },
        )

        assert response.status_code == 201

        result = await db_session.execute(
            select(EmailOtp).where(
                EmailOtp.purpose == EmailOtpPurpose.VERIFY_EMAIL,
            )
        )

        email_otp = result.scalars().first()

        assert email_otp is not None
        assert len(email_otp.otp_hash) == 64
        assert not email_otp.otp_hash.isdigit()
        assert email_otp.failed_attempts == 0
        assert email_otp.used_at is None
        assert email_otp.invalidated_at is None

    finally:
        app.dependency_overrides.pop(
            get_mailer,
            None,
        )
