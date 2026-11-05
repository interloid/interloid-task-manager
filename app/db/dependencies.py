import logging
from collections.abc import AsyncGenerator

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.workers.email_queue import enqueue_email

logger = logging.getLogger(__name__)


async def get_db(
    request: Request,
) -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session

            await session.commit()

            pending_emails = session.info.pop("pending_email_jobs", [])

            for email_data in pending_emails:
                try:
                    await enqueue_email(
                        request.app.state.arq_pool,
                        **email_data,
                    )
                except Exception:
                    logger.exception("Failed to enqueue email job")

            redis = getattr(request.app.state, "redis", None)
            pending_events = session.info.pop("pending_notification_events", [])

            if redis is not None:
                for event in pending_events:
                    try:
                        await redis.publish(
                            f"notifications:{event['user_id']}",
                            event["data"],
                        )
                    except Exception:
                        logger.exception("Failed to publish notification event")
        except Exception:
            await session.rollback()
            raise
