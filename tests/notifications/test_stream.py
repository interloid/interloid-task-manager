import pytest
from httpx import AsyncClient
from uuid import uuid4
from unittest.mock import AsyncMock

from fastapi import Request

from app.core.config import settings
from app.models import User
from app.services.sse_connection_manager import SSEConnectionManager


@pytest.mark.anyio
async def test_rejects_connection_when_limit_is_reached(
    client: AsyncClient,
    user_headers: dict[str, str],
    test_user: User,
    test_redis,
) -> None:
    redis = test_redis
    user_id = str(test_user.id)
    key = f"{settings.SSE_CONNECTION_KEY_PREFIX}:{user_id}"

    connection_ids = [
        f"test-connection-{index}"
        for index in range(settings.MAX_SSE_CONNECTIONS)
    ]

    try:
        for connection_id in connection_ids:
            acquired = await redis.zadd(
                key,
                {connection_id: 9999999999999},
            )
            assert acquired == 1

        response = await client.get(
            "/api/v1/notifications/stream",
            headers=user_headers,
        )

        assert response.status_code == 429

        response_data = response.json()
        assert (
            response_data["error"]["code"]
            == "SSE_CONNECTION_LIMIT_EXCEEDED"
        )

    finally:
        await redis.delete(key)


@pytest.mark.anyio
async def test_released_connection_allows_new_connection(
    test_redis,
    test_user: User,
) -> None:

    redis = test_redis
    manager = SSEConnectionManager(redis)

    user_id = str(test_user.id)
    key = f"{settings.SSE_CONNECTION_KEY_PREFIX}:{user_id}"

    connection_ids = [
        str(uuid4())
        for _ in range(settings.MAX_SSE_CONNECTIONS + 1)
    ]

    try:
        for connection_id in connection_ids[:settings.MAX_SSE_CONNECTIONS]:
            assert await manager.acquire(user_id, connection_id) is True

        await manager.release(user_id, connection_ids[0])

        result = await manager.acquire(
            user_id,
            connection_ids[-1],
        )

        assert result is True
        assert await redis.zcard(key) == settings.MAX_SSE_CONNECTIONS

    finally:
        await redis.delete(key)

@pytest.mark.anyio
async def test_sse_stream_connects_and_releases_connection(
    client: AsyncClient,
    test_user: User,
    user_headers: dict[str, str],
    test_redis,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    redis = test_redis
    user_id = str(test_user.id)
    key = f"{settings.SSE_CONNECTION_KEY_PREFIX}:{user_id}"

    pubsub = AsyncMock()
    pubsub.get_message.return_value = None

    monkeypatch.setattr(
        redis,
        "pubsub",
        lambda: pubsub,
    )

    monkeypatch.setattr(
        Request,
        "is_disconnected",
        AsyncMock(side_effect=[False, True]),
    )

    response = await client.get(
        "api/v1/notifications/stream",
        headers=user_headers,
    )

    assert response.status_code == 200
    assert "retry: 5000" in response.text
    assert ": heartbeat" in response.text

    assert await redis.zcard(key) == 0

    pubsub.subscribe.assert_awaited_once()
    pubsub.unsubscribe.assert_awaited_once()
    pubsub.aclose.assert_awaited_once()






    
