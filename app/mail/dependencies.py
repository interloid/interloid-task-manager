from app.mail.base import Mailer
from app.mail.smtp import SMTPMailer


def get_mailer() -> Mailer:
    return SMTPMailer()
