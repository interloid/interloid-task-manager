import time

from redis.asyncio import Redis

from app.core.config import settings

ACQUIRE_CONNECTION_SCRIPT = """
local key = KEYS[1]
local max_connections = tonumber(ARGV[1])
local connection_id = ARGV[2]
local expires_at = tonumber(ARGV[3])
local now = tonumber(ARGV[4])
local ttl = tonumber(ARGV[5])

redis.call('ZREMRANGEBYSCORE', key, '-inf', now)

local count = redis.call('ZCARD', key)

if count >= max_connections then
    return 0
end

redis.call('ZADD', key, expires_at, connection_id)
redis.call('PEXPIRE', key, ttl)

return 1
"""


RENEW_CONNECTION_SCRIPT = """
local key = KEYS[1]
local connection_id = ARGV[1]
local expires_at = tonumber(ARGV[2])
local now = tonumber(ARGV[3])
local ttl = tonumber(ARGV[4])

local current_expiry = redis.call('ZSCORE', key, connection_id)

if current_expiry == false then
    return 0
end

if tonumber(current_expiry) <= now then
    redis.call('ZREM', key, connection_id)
    return 0
end

redis.call('ZADD', key, expires_at, connection_id)
redis.call('PEXPIRE', key, ttl)

return 1
"""

RELEASE_CONNECTION_SCRIPT = """
local key = KEYS[1]
local connection_id = ARGV[1]

redis.call('ZREM', key, connection_id)

if redis.call('ZCARD', key) == 0 then
    redis.call('DEL', key)
end

return 1
"""


class SSEConnectionManager:
    def __init__(self, redis: Redis) -> None:
        self.redis = redis

    async def acquire(
        self,
        user_id: str,
        connection_id: str,
    ) -> bool:
        now = int(time.time() * 1000)
        ttl = settings.SSE_CONNECTION_TTL * 1000

        result = await self.redis.eval(
            ACQUIRE_CONNECTION_SCRIPT,
            1,
            f"{settings.SSE_CONNECTION_KEY_PREFIX}:{user_id}",
            settings.MAX_SSE_CONNECTIONS,
            connection_id,
            now + ttl,
            now,
            ttl,
        )

        return bool(result)

    async def renew(
        self,
        user_id: str,
        connection_id: str,
    ) -> bool:
        now = int(time.time() * 1000)
        ttl = settings.SSE_CONNECTION_TTL * 1000

        result = await self.redis.eval(
            RENEW_CONNECTION_SCRIPT,
            1,
            f"{settings.SSE_CONNECTION_KEY_PREFIX}:{user_id}",
            connection_id,
            now + ttl,
            now,
            ttl,
        )

        return bool(result)

    async def release(
        self,
        user_id: str,
        connection_id: str,
    ) -> None:
        await self.redis.eval(
            RELEASE_CONNECTION_SCRIPT,
            1,
            f"{settings.SSE_CONNECTION_KEY_PREFIX}:{user_id}",
            connection_id,
        )
