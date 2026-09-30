import re
from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password
from app.enums.email_otp import EmailOtpPurpose
from app.mail.dependencies import get_mailer
from app.mail.fake import FakeMailer
from app.main import app
from app.models.email_otp import EmailOtp
from app.models.user import User


async def test_reset_password_success(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    fake_mailer = FakeMailer()

    app.dependency_overrides[get_mailer] = lambda: fake_mailer

    try:
        register_response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "reset-success@example.com",
                "password": "password123",
                "first_name": "Amal",
                "last_name": "Das",
            },
        )

        assert register_response.status_code == 201

        fake_mailer.sent_emails.clear()

        forgot_response = await client.post(
            "/api/v1/auth/forgot-password",
            json={
                "email": "reset-success@example.com",
            },
        )

        assert forgot_response.status_code == 200
        assert len(fake_mailer.sent_emails) == 1

        email = fake_mailer.sent_emails[0]

        match = re.search(
            r"\b\d{6}\b",
            email["text_body"],
        )

        assert match is not None

        otp = match.group()
        reset_response = await client.post(
            "/api/v1/auth/reset-password",
            json={
                "email": "reset-success@example.com",
                "otp": otp,
                "new_password": "newpassword123",
            },
        )

        assert reset_response.status_code == 200

        body = reset_response.json()

        assert body["success"] is True
        assert body["message"] == "Password reset successfully"

        user_result = await db_session.execute(
            select(User).where(
                User.email == "reset-success@example.com",
            )
        )

        user = user_result.scalar_one()

        await db_session.refresh(user)

        assert verify_password(
            "newpassword123",
            user.password_hash,
        )

        assert user.password_changed_at is not None

        otp_result = await db_session.execute(
            select(EmailOtp).where(
                EmailOtp.user_id == user.id,
                EmailOtp.purpose == EmailOtpPurpose.RESET_PASSWORD,
            )
        )

        reset_otp = otp_result.scalar_one()

        await db_session.refresh(reset_otp)

        assert reset_otp.used_at is not None
        assert reset_otp.invalidated_at is None

    finally:
        app.dependency_overrides.pop(
            get_mailer,
            None,
        )


async def test_reset_password_wrong_otp_returns_400(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    fake_mailer = FakeMailer()

    app.dependency_overrides[get_mailer] = lambda: fake_mailer

    try:
        register_response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "reset-wrong-otp@example.com",
                "password": "password123",
                "first_name": "Amal",
                "last_name": "Das",
            },
        )

        assert register_response.status_code == 201

        fake_mailer.sent_emails.clear()

        forgot_response = await client.post(
            "/api/v1/auth/forgot-password",
            json={
                "email": "reset-wrong-otp@example.com",
            },
        )

        assert forgot_response.status_code == 200

        reset_response = await client.post(
            "/api/v1/auth/reset-password",
            json={
                "email": "reset-wrong-otp@example.com",
                "otp": "111111",
                "new_password": "newpassword123",
            },
        )

        assert reset_response.status_code == 400

        body = reset_response.json()

        assert body["success"] is False
        assert body["error"]["code"] == "INVALID_EMAIL_OTP"

        user_result = await db_session.execute(
            select(User).where(
                User.email == "reset-wrong-otp@example.com",
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

        await db_session.refresh(reset_otp)

        assert reset_otp.failed_attempts == 1
        assert reset_otp.used_at is None
        assert reset_otp.invalidated_at is None

        await db_session.refresh(user)

        assert verify_password(
            "password123",
            user.password_hash,
        )

    finally:
        app.dependency_overrides.pop(
            get_mailer,
            None,
        )


async def test_reset_password_fifth_wrong_otp_invalidates_otp(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    fake_mailer = FakeMailer()

    app.dependency_overrides[get_mailer] = lambda: fake_mailer

    try:
        register_response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "reset-max-attempts@example.com",
                "password": "password123",
                "first_name": "Amal",
                "last_name": "Das",
            },
        )

        assert register_response.status_code == 201

        fake_mailer.sent_emails.clear()

        forgot_response = await client.post(
            "/api/v1/auth/forgot-password",
            json={
                "email": "reset-max-attempts@example.com",
            },
        )

        assert forgot_response.status_code == 200

        for _ in range(4):
            response = await client.post(
                "/api/v1/auth/reset-password",
                json={
                    "email": "reset-max-attempts@example.com",
                    "otp": "111111",
                    "new_password": "newpassword123",
                },
            )

            assert response.status_code == 400
            assert response.json()["error"]["code"] == "INVALID_EMAIL_OTP"

        response = await client.post(
            "/api/v1/auth/reset-password",
            json={
                "email": "reset-max-attempts@example.com",
                "otp": "111111",
                "new_password": "newpassword123",
            },
        )

        assert response.status_code == 429

        body = response.json()

        assert body["success"] is False
        assert body["error"]["code"] == "EMAIL_OTP_ATTEMPTS_EXCEEDED"

        user_result = await db_session.execute(
            select(User).where(
                User.email == "reset-max-attempts@example.com",
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

        await db_session.refresh(reset_otp)

        assert reset_otp.failed_attempts == 5
        assert reset_otp.invalidated_at is not None
        assert reset_otp.used_at is None

        await db_session.refresh(user)

        assert verify_password(
            "password123",
            user.password_hash,
        )

    finally:
        app.dependency_overrides.pop(
            get_mailer,
            None,
        )


async def test_reset_password_same_as_current_returns_422(
    client: AsyncClient,
) -> None:
    fake_mailer = FakeMailer()

    app.dependency_overrides[get_mailer] = lambda: fake_mailer

    try:
        register_response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "reset-same-password@example.com",
                "password": "password123",
                "first_name": "Amal",
                "last_name": "Das",
            },
        )

        assert register_response.status_code == 201

        fake_mailer.sent_emails.clear()

        forgot_response = await client.post(
            "/api/v1/auth/forgot-password",
            json={
                "email": "reset-same-password@example.com",
            },
        )

        assert forgot_response.status_code == 200
        assert len(fake_mailer.sent_emails) == 1

        email = fake_mailer.sent_emails[0]

        match = re.search(
            r"\b\d{6}\b",
            email["text_body"],
        )

        assert match is not None

        otp = match.group()

        response = await client.post(
            "/api/v1/auth/reset-password",
            json={
                "email": "reset-same-password@example.com",
                "otp": otp,
                "new_password": "password123",
            },
        )

        assert response.status_code == 422

        body = response.json()

        assert body["success"] is False
        assert body["error"]["code"] == "PASSWORD_REUSE_NOT_ALLOWED"

    finally:
        app.dependency_overrides.pop(
            get_mailer,
            None,
        )


async def test_reset_password_reuse_error_keeps_otp_usable(
    client: AsyncClient,
) -> None:
    fake_mailer = FakeMailer()

    app.dependency_overrides[get_mailer] = lambda: fake_mailer

    try:
        register_response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "reset-retry@example.com",
                "password": "password123",
                "first_name": "Amal",
                "last_name": "Das",
            },
        )

        assert register_response.status_code == 201

        fake_mailer.sent_emails.clear()

        forgot_response = await client.post(
            "/api/v1/auth/forgot-password",
            json={
                "email": "reset-retry@example.com",
            },
        )

        assert forgot_response.status_code == 200
        assert len(fake_mailer.sent_emails) == 1

        email = fake_mailer.sent_emails[0]

        match = re.search(
            r"\b\d{6}\b",
            email["text_body"],
        )

        assert match is not None

        otp = match.group()

        first_response = await client.post(
            "/api/v1/auth/reset-password",
            json={
                "email": "reset-retry@example.com",
                "otp": otp,
                "new_password": "password123",
            },
        )

        assert first_response.status_code == 422
        assert first_response.json()["error"]["code"] == "PASSWORD_REUSE_NOT_ALLOWED"

        second_response = await client.post(
            "/api/v1/auth/reset-password",
            json={
                "email": "reset-retry@example.com",
                "otp": otp,
                "new_password": "newpassword123",
            },
        )

        assert second_response.status_code == 200

        body = second_response.json()

        assert body["success"] is True
        assert body["message"] == "Password reset successfully"

    finally:
        app.dependency_overrides.pop(
            get_mailer,
            None,
        )


async def test_reset_password_expired_otp_returns_400(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    fake_mailer = FakeMailer()

    app.dependency_overrides[get_mailer] = lambda: fake_mailer

    try:
        register_response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "reset-expired@example.com",
                "password": "password123",
                "first_name": "Amal",
                "last_name": "Das",
            },
        )

        assert register_response.status_code == 201

        fake_mailer.sent_emails.clear()

        forgot_response = await client.post(
            "/api/v1/auth/forgot-password",
            json={
                "email": "reset-expired@example.com",
            },
        )

        assert forgot_response.status_code == 200
        assert len(fake_mailer.sent_emails) == 1

        email = fake_mailer.sent_emails[0]

        match = re.search(
            r"\b\d{6}\b",
            email["text_body"],
        )

        assert match is not None

        otp = match.group()

        user_result = await db_session.execute(
            select(User).where(
                User.email == "reset-expired@example.com",
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

        reset_otp.expires_at = datetime.now(UTC) - timedelta(minutes=1)

        await db_session.commit()

        response = await client.post(
            "/api/v1/auth/reset-password",
            json={
                "email": "reset-expired@example.com",
                "otp": otp,
                "new_password": "newpassword123",
            },
        )

        assert response.status_code == 400

        body = response.json()

        assert body["success"] is False
        assert body["error"]["code"] == "INVALID_EMAIL_OTP"

        await db_session.refresh(user)

        assert verify_password(
            "password123",
            user.password_hash,
        )

    finally:
        app.dependency_overrides.pop(
            get_mailer,
            None,
        )


async def test_reset_password_revokes_all_refresh_sessions(
    client: AsyncClient,
) -> None:
    fake_mailer = FakeMailer()

    app.dependency_overrides[get_mailer] = lambda: fake_mailer

    try:
        email_address = "reset-sessions@example.com"
        old_password = "password123"
        new_password = "newpassword123"

        register_response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": email_address,
                "password": old_password,
                "first_name": "Amal",
                "last_name": "Das",
            },
        )

        assert register_response.status_code == 201
        assert len(fake_mailer.sent_emails) == 1

        verification_email = fake_mailer.sent_emails[0]

        verification_match = re.search(
            r"\b\d{6}\b",
            verification_email["text_body"],
        )

        assert verification_match is not None

        verification_otp = verification_match.group()

        verify_response = await client.post(
            "/api/v1/auth/verify-email",
            json={
                "email": email_address,
                "otp": verification_otp,
            },
        )

        assert verify_response.status_code == 200

        first_login = await client.post(
            "/api/v1/auth/login",
            json={
                "email": email_address,
                "password": old_password,
            },
        )

        assert first_login.status_code == 200

        second_login = await client.post(
            "/api/v1/auth/login",
            json={
                "email": email_address,
                "password": old_password,
            },
        )

        assert second_login.status_code == 200

        first_refresh_token = first_login.json()["data"]["refresh_token"]

        second_refresh_token = second_login.json()["data"]["refresh_token"]

        assert first_refresh_token != second_refresh_token

        fake_mailer.sent_emails.clear()

        forgot_response = await client.post(
            "/api/v1/auth/forgot-password",
            json={
                "email": email_address,
            },
        )

        assert forgot_response.status_code == 200
        assert len(fake_mailer.sent_emails) == 1

        reset_email = fake_mailer.sent_emails[0]

        reset_match = re.search(
            r"\b\d{6}\b",
            reset_email["text_body"],
        )

        assert reset_match is not None

        reset_otp = reset_match.group()

        reset_response = await client.post(
            "/api/v1/auth/reset-password",
            json={
                "email": email_address,
                "otp": reset_otp,
                "new_password": new_password,
            },
        )

        assert reset_response.status_code == 200

        first_refresh_response = await client.post(
            "/api/v1/auth/refresh",
            json={
                "refresh_token": first_refresh_token,
            },
        )

        assert first_refresh_response.status_code == 401

        second_refresh_response = await client.post(
            "/api/v1/auth/refresh",
            json={
                "refresh_token": second_refresh_token,
            },
        )

        assert second_refresh_response.status_code == 401

    finally:
        app.dependency_overrides.pop(
            get_mailer,
            None,
        )


async def test_reset_password_invalidates_old_access_token(
    client: AsyncClient,
) -> None:
    fake_mailer = FakeMailer()

    app.dependency_overrides[get_mailer] = lambda: fake_mailer

    try:
        email_address = "reset-access-token@example.com"
        old_password = "password123"
        new_password = "newpassword123"

        register_response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": email_address,
                "password": old_password,
                "first_name": "Amal",
                "last_name": "Das",
            },
        )

        assert register_response.status_code == 201
        assert len(fake_mailer.sent_emails) == 1

        verification_email = fake_mailer.sent_emails[0]

        verification_match = re.search(
            r"\b\d{6}\b",
            verification_email["text_body"],
        )

        assert verification_match is not None

        verification_otp = verification_match.group()

        verify_response = await client.post(
            "/api/v1/auth/verify-email",
            json={
                "email": email_address,
                "otp": verification_otp,
            },
        )

        assert verify_response.status_code == 200

        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": email_address,
                "password": old_password,
            },
        )

        assert login_response.status_code == 200

        old_access_token = login_response.json()["data"]["access_token"]

        me_before_reset = await client.get(
            "/api/v1/users/me",
            headers={
                "Authorization": f"Bearer {old_access_token}",
            },
        )

        assert me_before_reset.status_code == 200

        fake_mailer.sent_emails.clear()

        forgot_response = await client.post(
            "/api/v1/auth/forgot-password",
            json={
                "email": email_address,
            },
        )

        assert forgot_response.status_code == 200
        assert len(fake_mailer.sent_emails) == 1

        reset_email = fake_mailer.sent_emails[0]

        reset_match = re.search(
            r"\b\d{6}\b",
            reset_email["text_body"],
        )

        assert reset_match is not None

        reset_otp = reset_match.group()

        reset_response = await client.post(
            "/api/v1/auth/reset-password",
            json={
                "email": email_address,
                "otp": reset_otp,
                "new_password": new_password,
            },
        )

        assert reset_response.status_code == 200

        me_after_reset = await client.get(
            "/api/v1/users/me",
            headers={
                "Authorization": f"Bearer {old_access_token}",
            },
        )

        assert me_after_reset.status_code == 401

    finally:
        app.dependency_overrides.pop(
            get_mailer,
            None,
        )


async def test_reset_password_old_password_fails_new_password_succeeds(
    client: AsyncClient,
) -> None:
    fake_mailer = FakeMailer()

    app.dependency_overrides[get_mailer] = lambda: fake_mailer

    try:
        email_address = "reset-login@example.com"
        old_password = "password123"
        new_password = "newpassword123"

        register_response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": email_address,
                "password": old_password,
                "first_name": "Amal",
                "last_name": "Das",
            },
        )

        assert register_response.status_code == 201

        verification_email = fake_mailer.sent_emails[0]

        verification_match = re.search(
            r"\b\d{6}\b",
            verification_email["text_body"],
        )

        assert verification_match is not None

        verification_otp = verification_match.group()

        verify_response = await client.post(
            "/api/v1/auth/verify-email",
            json={
                "email": email_address,
                "otp": verification_otp,
            },
        )

        assert verify_response.status_code == 200

        fake_mailer.sent_emails.clear()

        forgot_response = await client.post(
            "/api/v1/auth/forgot-password",
            json={
                "email": email_address,
            },
        )

        assert forgot_response.status_code == 200
        assert len(fake_mailer.sent_emails) == 1

        reset_email = fake_mailer.sent_emails[0]

        reset_match = re.search(
            r"\b\d{6}\b",
            reset_email["text_body"],
        )

        assert reset_match is not None

        reset_otp = reset_match.group()

        reset_response = await client.post(
            "/api/v1/auth/reset-password",
            json={
                "email": email_address,
                "otp": reset_otp,
                "new_password": new_password,
            },
        )

        assert reset_response.status_code == 200

        old_login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": email_address,
                "password": old_password,
            },
        )

        assert old_login_response.status_code == 401

        new_login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": email_address,
                "password": new_password,
            },
        )

        assert new_login_response.status_code == 200

    finally:
        app.dependency_overrides.pop(
            get_mailer,
            None,
        )
