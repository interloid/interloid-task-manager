import time
from math import ceil

from limits import RateLimitItemPerMinute
from limits.aio.storage import RedisStorage, MemoryStorage
from limits.aio.strategies import MovingWindowRateLimiter

from app.core.config import settings


class LoginRateLimiter:
    def __init__(
        self,
        storage: RedisStorage | MemoryStorage | None = None, 
    ) -> None:
        self.storage = storage or RedisStorage(
            settings.REDIS_URL,
            implementation="redispy",
            key_prefix=settings.REDIS_KEY_PREFIX,
        )

        self.limiter = MovingWindowRateLimiter(
            self.storage,
        )

        self.email_limit = RateLimitItemPerMinute(
            amount=5,
            multiples=1,
            namespace="login_email_failures",
        )

        self.ip_limit = RateLimitItemPerMinute(
            amount=30,
            multiples=1,
            namespace="login_ip_failures",
        )

    @staticmethod
    def normalize_email(
        email: str,
    ) -> str:
        return email.strip().lower()

    async def get_retry_after(
        self,
        *,
        client_ip: str | None,
        email: str,
    ) -> int | None:
        normalized_email = self.normalize_email(
            email,
        )

        identifiers: list[tuple[RateLimitItemPerMinute, str, str]] = [
            (
                self.email_limit,
                "email", 
                normalized_email,
            ),
        ]

        if client_ip is not None:
            identifiers.append(
                (
                    self.ip_limit,
                    "ip", 
                    client_ip
                ),
            )

        retry_after_values: list[int] = []

        for limit, scope, value in identifiers:
            allowed = await self.limiter.test(
                limit,
                scope,
                value,
            )

            if allowed:
                continue

            stats = await self.limiter.get_window_stats(
                limit,
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
        client_ip: str | None,
        email: str,
    ) -> None:
        normalized_email = self.normalize_email(
            email,
        )

        if client_ip is not None:
            await self.limiter.hit(
                self.ip_limit,
                "ip",
                client_ip,  
            )

        await self.limiter.hit(
            self.email_limit,
            "email",
            normalized_email,
        )

    async def reset(self) -> None:
        await self.storage.reset()


login_rate_limiter = LoginRateLimiter()
