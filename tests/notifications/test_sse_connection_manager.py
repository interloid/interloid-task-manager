import time
from uuid import uuid4

import pytest
from redis.asyncio import Redis

from app.core.config import settings
from app.services.sse_connection_manager import SSEConnectionManager


async def create_connection_manager() -> tuple[
    Redis,
    SSEConnectionManager,
    str,
    str,
]:
    redis = Redis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
    )

    user_id = str(uuid4())
    key = f"{settings.SSE_CONNECTION_KEY_PREFIX}:{user_id}"

    manager = SSEConnectionManager(redis)

    return redis, manager, user_id, key


@pytest.mark.anyio
async def test_acquire_connection() -> None:
    redis, manager, user_id, key = await create_connection_manager()

    try:
        connection_id = str(uuid4())

        result = await manager.acquire(user_id, connection_id)

        assert result is True
        assert await redis.zscore(key, connection_id) is not None

    finally:
        await redis.delete(key)
        await redis.aclose()


@pytest.mark.anyio
async def test_rejects_connection_when_limit_is_reached() -> None:
    redis, manager, user_id, key = await create_connection_manager()

    try:
        connection_ids = [str(uuid4()) for _ in range(4)]

        for connection_id in connection_ids[:settings.MAX_SSE_CONNECTIONS]:
            result = await manager.acquire(user_id, connection_id)
            assert result is True

        result = await manager.acquire(
            user_id,
            connection_ids[settings.MAX_SSE_CONNECTIONS],
        )

        assert result is False
        assert await redis.zcard(key) == settings.MAX_SSE_CONNECTIONS

    finally:
        await redis.delete(key)
        await redis.aclose()


@pytest.mark.anyio
async def test_release_connection_frees_slot() -> None:
    redis, manager, user_id, key = await create_connection_manager()

    try:
        connection_ids = [str(uuid4()) for _ in range(4)]

        for connection_id in connection_ids[:settings.MAX_SSE_CONNECTIONS]:
            assert await manager.acquire(user_id, connection_id) is True

        await manager.release(user_id, connection_ids[0])

        result = await manager.acquire(
            user_id,
            connection_ids[settings.MAX_SSE_CONNECTIONS],
        )

        assert result is True
        assert await redis.zcard(key) == settings.MAX_SSE_CONNECTIONS

    finally:
        await redis.delete(key)
        await redis.aclose()


@pytest.mark.anyio
async def test_renew_active_connection() -> None:
    redis, manager, user_id, key = await create_connection_manager()

    try:
        connection_id = str(uuid4())

        assert await manager.acquire(user_id, connection_id) is True

        previous_expiry = await redis.zscore(key, connection_id)

        result = await manager.renew(user_id, connection_id)

        new_expiry = await redis.zscore(key, connection_id)

        assert result is True
        assert new_expiry is not None
        assert previous_expiry is not None
        assert new_expiry >= previous_expiry

    finally:
        await redis.delete(key)
        await redis.aclose()


@pytest.mark.anyio
async def test_expired_connection_cannot_be_renewed() -> None:
    redis, manager, user_id, key = await create_connection_manager()

    try:
        connection_id = str(uuid4())
        expired_at = int(time.time() * 1000) - 1000

        await redis.zadd(key, {connection_id: expired_at})

        result = await manager.renew(user_id, connection_id)

        assert result is False
        assert await redis.zscore(key, connection_id) is None

    finally:
        await redis.delete(key)
        await redis.aclose()

    