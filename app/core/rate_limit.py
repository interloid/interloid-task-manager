import time
from math import ceil

from limits import RateLimitItemPerMinute
from limits.aio.storage import RedisStorage
from limits.aio.strategies import MovingWindowRateLimiter

from app.core.config import settings


class LoginRateLimiter:
    def __init__(self) -> None:
        self.storage = RedisStorage(
            settings.REDIS_URL,
            implementation="redispy",
            key_prefix=settings.REDIS_KEY_PREFIX,
        )

        self.limiter = MovingWindowRateLimiter(
            self.storage,
        )

        self.limit = RateLimitItemPerMinute(
            amount=5,
            multiples=1,
            namespace="login_failures",
        )

    @staticmethod
    def normalize_email(
        email: str,
    ) -> str:
        return email.strip().lower()

    async def get_retry_after(
        self,
        *,
        client_ip: str,
        email: str,
    ) -> int | None:
        normalized_email = self.normalize_email(
            email,
        )

        identifiers = (
            ("ip", client_ip),
            ("email", normalized_email),
        )

        retry_after_values: list[int] = []

        for scope, value in identifiers:
            allowed = await self.limiter.test(
                self.limit,
                scope,
                value,
            )

            if allowed:
                continue

            stats = await self.limiter.get_window_stats(
                self.limit,
                scope,
                value,
            )

            retry_after = max(
                1,
                ceil(stats.reset_time - time.time()),
            )

            retry_after_values.append(
                retry_after,
            )

        if not retry_after_values:
            return None

        return max(retry_after_values)

    async def record_failure(
        self,
        *,
        client_ip: str,
        email: str,
    ) -> None:
        normalized_email = self.normalize_email(
            email,
        )

        await self.limiter.hit(
            self.limit,
            "ip",
            client_ip,
        )

        await self.limiter.hit(
            self.limit,
            "email",
            normalized_email,
        )

    async def reset(self) -> None:
        await self.storage.reset()


login_rate_limiter = LoginRateLimiter()
