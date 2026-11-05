import logging
from typing import Any, ClassVar

from arq.connections import RedisSettings
from arq.worker import Retry

from app.core.config import settings
from app.mail.smtp import SMTPMailer

logger = logging.getLogger(__name__)


async def send_email_job(
    ctx: dict[str, Any],
    *,
    to_email: str,
    subject: str,
    text_body: str,
    html_body: str,
) -> None:
    mailer: SMTPMailer = ctx["mailer"]

    try:
        await mailer.send_email(
            to_email=to_email,
            subject=subject,
            text_body=text_body,
            html_body=html_body,
        )
    except Exception as err:
        logger.exception(
            "Email job failed | to=%s | subject=%s",
            to_email,
            subject,
        )
        raise Retry(defer=5) from err

    logger.info(
        "Email job completed | to=%s",
        to_email,
    )


async def startup(ctx: dict[str, Any]) -> None:
    ctx["mailer"] = SMTPMailer()
    logger.info("ARQ email worker started successfully")


class WorkerSettings:
    functions: ClassVar[list] = [send_email_job]
    on_startup = startup
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    max_jobs = 10
    job_timeout = 60
    max_tries = 3
