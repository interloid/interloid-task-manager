import logging
from email.message import EmailMessage

import aiosmtplib

from app.core.config import settings

logger = logging.getLogger(__name__)


class SMTPMailer:
    async def send_email(
        self,
        *,
        to_email: str,
        subject: str,
        text_body: str,
        html_body: str,
    ) -> None:
        message = EmailMessage()

        message["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
        message["To"] = to_email
        message["Subject"] = subject

        message.set_content(
            text_body,
        )

        message.add_alternative(
            html_body,
            subtype="html",
        )

        logger.info(
            "Sending email | to=%s | host=%s | port=%s",
            to_email,
            settings.SMTP_HOST,
            settings.SMTP_PORT,
        )

        try:
            await aiosmtplib.send(
                message,
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                username=settings.SMTP_USERNAME,
                password=settings.SMTP_PASSWORD.get_secret_value(),
                start_tls=settings.SMTP_USE_TLS,
            )

            logger.info(
                "Email successfully accepted by SMTP server | to=%s",
                to_email,
            )

        except Exception:
            logger.exception(
                "Failed to send email | to=%s",
                to_email,
            )
            raise
