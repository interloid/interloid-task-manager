class FakeMailer:
    def __init__(self) -> None:
        self.sent_emails: list[dict[str, str]] = []

    async def send_email(
        self,
        *,
        to_email: str,
        subject: str,
        text_body: str,
        html_body: str,
    ) -> None:
        self.sent_emails.append(
            {
                "to_email": to_email,
                "subject": subject,
                "text_body": text_body,
                "html_body": html_body,
            }
        )
