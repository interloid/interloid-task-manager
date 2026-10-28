from arq import create_pool
from arq.connections import RedisSettings

from app.core.config import settings


async def enqueue_email(
    *,
    to_email: str,
    subject: str,
    text_body: str,
    html_body: str,
) -> None:
    redis_pool = await create_pool(RedisSettings.from_dsn(settings.REDIS_URL))

    try:
        await redis_pool.enqueue_job(
            "send_email_job",
            to_email=to_email,
            subject=subject,
            text_body=text_body,
            html_body=html_body,
        )
    finally:
        await redis_pool.aclose()
