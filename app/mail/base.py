from typing import Protocol


class Mailer(Protocol):
    async def send_email(
        self,
        *,
        to_email: str,
        subject: str,
        text_body: str,
        html_body: str,
    ) -> None: ...
