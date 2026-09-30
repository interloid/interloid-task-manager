from datetime import UTC, datetime, timedelta
from math import ceil

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import hash_password, verify_password
from app.enums.email_otp import EmailOtpPurpose
from app.exceptions.auth import (
    EmailAlreadyVerifiedException,
    EmailOtpAttemptsExceededException,
    EmailOtpResendCooldownException,
    InvalidEmailOtpException,
    PasswordReuseNotAllowedException,
)
from app.mail.base import Mailer
from app.mail.renderer import render_template
from app.models.email_otp import EmailOtp
from app.models.user import User
from app.repositories.email_otp import EmailOtpRepository
from app.repositories.refresh_token import RefreshTokenRepository
from app.repositories.user import UserRepository
from app.utils.otp import generate_otp, hash_otp, verify_otp


class EmailVerificationService:
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.session = session
        self.email_otp_repository = EmailOtpRepository(session)
        self.user_repository = UserRepository(session)
        self.refresh_token_repository = RefreshTokenRepository(session)

    async def create_verification_otp(
        self,
        user: User,
    ) -> str:
        otp = generate_otp()

        email_otp = EmailOtp(
            user_id=user.id,
            purpose=EmailOtpPurpose.VERIFY_EMAIL,
            otp_hash=hash_otp(otp),
            expires_at=(
                datetime.now(UTC)
                + timedelta(
                    minutes=settings.EMAIL_OTP_EXPIRE_MINUTES,
                )
            ),
            failed_attempts=0,
        )

        await self.email_otp_repository.create(
            email_otp,
        )

        return otp

    async def send_verification_otp(
        self,
        user: User,
        mailer: Mailer,
    ) -> None:
        otp = await self.create_verification_otp(
            user,
        )

        html_body = render_template(
            "verification_otp.html",
            first_name=user.first_name,
            otp=otp,
            app_name=settings.APP_NAME,
            expiry_minutes=settings.EMAIL_OTP_EXPIRE_MINUTES,
        )

        text_body = (
            f"Hello {user.first_name},\n\n"
            f"Your verification code is {otp}.\n"
            f"This code expires in "
            f"{settings.EMAIL_OTP_EXPIRE_MINUTES} minutes.\n\n"
            "If you did not create this account, "
            "you can safely ignore this email."
        )

        await mailer.send_email(
            to_email=user.email,
            subject="Verify your email",
            text_body=text_body,
            html_body=html_body,
        )

    async def verify_email(
        self,
        *,
        email: str,
        otp: str,
    ) -> None:
        user = await self.user_repository.get_by_email(email)

        if user is None:
            raise InvalidEmailOtpException()

        if user.is_verified:
            raise EmailAlreadyVerifiedException()

        email_otp = await self.email_otp_repository.get_active_for_update(
            user_id=user.id, purpose=EmailOtpPurpose.VERIFY_EMAIL
        )

        if email_otp is None:
            raise InvalidEmailOtpException()

        if email_otp.failed_attempts >= settings.EMAIL_OTP_MAX_ATTEMPTS:
            raise EmailOtpAttemptsExceededException()

        if not verify_otp(
            otp,
            email_otp.otp_hash,
        ):
            await self.email_otp_repository.increment_failed_attempts(
                email_otp,
            )

            if email_otp.failed_attempts >= settings.EMAIL_OTP_MAX_ATTEMPTS:
                await self.email_otp_repository.invalidate(email_otp)

                await self.session.commit()

                raise EmailOtpAttemptsExceededException()

            await self.session.commit()

            raise InvalidEmailOtpException()

        await self.email_otp_repository.mark_used(
            email_otp,
        )

        user.is_verified = True

        await self.session.flush()

    async def resend_verification_otp(
        self,
        *,
        email: str,
        mailer: Mailer,
    ) -> None:
        user = await self.user_repository.get_by_email(email)

        if user is None:
            return

        if user.is_verified:
            raise EmailAlreadyVerifiedException()

        latest_otp = await self.email_otp_repository.get_latest_for_update(
            user_id=user.id,
            purpose=EmailOtpPurpose.VERIFY_EMAIL,
        )

        if latest_otp is not None:
            elapsed_seconds = (
                datetime.now(UTC) - latest_otp.created_at
            ).total_seconds()

            cooldown = settings.EMAIL_OTP_RESEND_COOLDOWN_SECONDS

            if elapsed_seconds < cooldown:
                retry_after = ceil(cooldown - elapsed_seconds)

                raise EmailOtpResendCooldownException(
                    retry_after=retry_after,
                )

        await self.email_otp_repository.invalidate_active(
            user_id=user.id,
            purpose=EmailOtpPurpose.VERIFY_EMAIL,
        )

        await self.send_verification_otp(
            user,
            mailer,
        )

    async def forgot_password(
        self,
        *,
        email: str,
        mailer: Mailer,
    ) -> None:
        user = await self.user_repository.get_by_email(email)

        if user is None:
            return

        await self.email_otp_repository.invalidate_active(
            user_id=user.id,
            purpose=EmailOtpPurpose.RESET_PASSWORD,
        )

        otp = generate_otp()

        email_otp = EmailOtp(
            user_id=user.id,
            purpose=EmailOtpPurpose.RESET_PASSWORD,
            otp_hash=hash_otp(otp),
            expires_at=(
                datetime.now(UTC)
                + timedelta(
                    minutes=settings.EMAIL_OTP_EXPIRE_MINUTES,
                )
            ),
            failed_attempts=0,
        )

        await self.email_otp_repository.create(
            email_otp,
        )

        html_body = render_template(
            "password_reset_otp.html",
            first_name=user.first_name,
            otp=otp,
            app_name=settings.APP_NAME,
            expiry_minutes=settings.EMAIL_OTP_EXPIRE_MINUTES,
        )

        text_body = (
            f"Hello {user.first_name},\n\n"
            f"Your password reset code is {otp}.\n"
            f"This code expires in "
            f"{settings.EMAIL_OTP_EXPIRE_MINUTES} minutes.\n\n"
            "If you did not request a password reset, "
            "you can safely ignore this email."
        )

        await mailer.send_email(
            to_email=user.email,
            subject="Reset your password",
            text_body=text_body,
            html_body=html_body,
        )

    async def reset_password(
        self,
        *,
        email: str,
        otp: str,
        new_password: str,
    ) -> None:
        user = await self.user_repository.get_by_email(email)

        if user is None:
            raise InvalidEmailOtpException()

        email_otp = await self.email_otp_repository.get_active_for_update(
            user_id=user.id,
            purpose=EmailOtpPurpose.RESET_PASSWORD,
        )

        if email_otp is None:
            raise InvalidEmailOtpException()

        if email_otp.failed_attempts >= settings.EMAIL_OTP_MAX_ATTEMPTS:
            raise EmailOtpAttemptsExceededException()

        if not verify_otp(
            otp,
            email_otp.otp_hash,
        ):
            await self.email_otp_repository.increment_failed_attempts(
                email_otp,
            )

            if email_otp.failed_attempts >= settings.EMAIL_OTP_MAX_ATTEMPTS:
                await self.email_otp_repository.invalidate(
                    email_otp,
                )

                await self.session.commit()

                raise EmailOtpAttemptsExceededException()

            await self.session.commit()

            raise InvalidEmailOtpException()

        if verify_password(
            new_password,
            user.password_hash,
        ):
            raise PasswordReuseNotAllowedException()

        new_password_hash = hash_password(
            new_password,
        )

        await self.user_repository.update_password(
            user,
            new_password_hash,
        )

        await self.email_otp_repository.mark_used(
            email_otp,
        )

        await self.refresh_token_repository.revoke_all_for_user(
            user.id,
        )
