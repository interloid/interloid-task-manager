import pytest
from arq.worker import Retry

from app.workers.email_worker import send_email_job


class FakeMailer:
    def __init__(self) -> None:
        self.attempts = 0

    async def send_email(
        self,
        *,
        to_email: str,
        subject: str,
        text_body: str,
        html_body: str,
    ) -> None:
        self.attempts += 1
        raise RuntimeError("Simulated SMTP failure")


@pytest.mark.asyncio
async def test_email_job_requests_retry_on_smtp_failure() -> None:
    mailer = FakeMailer()
    ctx = {"mailer": mailer}

    with pytest.raises(Retry) as exc_info:
        await send_email_job(
            ctx,
            to_email="recipient@example.com",
            subject="Test email",
            text_body="Test",
            html_body="<p>Test</p>",
        )

    assert mailer.attempts == 1
    assert exc_info.value.defer_score == 5000
