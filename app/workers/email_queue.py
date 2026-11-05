from arq.connections import ArqRedis


async def enqueue_email(
    redis_pool: ArqRedis,
    *,
    to_email: str,
    subject: str,
    text_body: str,
    html_body: str,
) -> None:
    await redis_pool.enqueue_job(
        "send_email_job",
        to_email=to_email,
        subject=subject,
        text_body=text_body,
        html_body=html_body,
    )
