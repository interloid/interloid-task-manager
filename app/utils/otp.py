import hashlib
import hmac
import secrets

from app.core.config import settings


def generate_otp() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_otp(
    otp: str,
) -> str:
    return hmac.new(
        settings.OTP_SECRET_KEY.get_secret_value().encode(),
        otp.encode(),
        hashlib.sha256,
    ).hexdigest()


def verify_otp(
    otp: str,
    stored_hash: str,
) -> bool:
    calculated_hash = hash_otp(
        otp,
    )

    return hmac.compare_digest(
        calculated_hash,
        stored_hash,
    )
