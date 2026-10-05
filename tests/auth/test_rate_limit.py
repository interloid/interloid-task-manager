from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.user import User


@pytest.fixture
async def client_with_ip() -> AsyncGenerator[
    tuple[AsyncClient, str],
    None,
]:
    client_ip = "192.168.1.100"

    transport = ASGITransport(
        app=app,
        client=(client_ip, 12345),
    )

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as async_client:
        yield async_client, client_ip


async def test_login_rate_limit_returns_429_after_five_failures(
    client: AsyncClient,
    test_user: User,
) -> None:
    login_data = {
        "email": test_user.email,
        "password": "WrongPassword123!",
    }

    for _ in range(5):
        response = await client.post(
            "/api/v1/auth/login",
            json=login_data,
        )

        assert response.status_code == 401

    response = await client.post(
        "/api/v1/auth/login",
        json=login_data,
    )

    assert response.status_code == 429

    body = response.json()

    assert body["success"] is False
    assert "Retry-After" in response.headers


async def test_login_rate_limit_is_applied_per_email(
    client_with_ip: tuple[AsyncClient, str],
    test_user: User,
) -> None:
    email = test_user.email

    for index in range(5):
        client_ip = f"192.168.1.{index + 1}"

        transport = ASGITransport(
            app=app,
            client=(client_ip, 12345),
        )

        async with AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/v1/auth/login",
                json={
                    "email": email,
                    "password": "WrongPassword123!",
                },
            )

        assert response.status_code == 401

    response = await client_with_ip[0].post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": "WrongPassword123!",
        },
    )

    assert response.status_code == 429


async def test_login_rate_limit_is_applied_per_ip(
    client_with_ip: tuple[AsyncClient, str],
) -> None:
    client, _ = client_with_ip

    for index in range(5):
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": f"user{index}@example.com",
                "password": "WrongPassword123!",
            },
        )

        assert response.status_code == 401

    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "another@example.com",
            "password": "WrongPassword123!",
        },
    )

    assert response.status_code == 429


async def test_login_rate_limit_retry_after_header_is_positive(
    client: AsyncClient,
    test_user: User,
) -> None:
    login_data = {
        "email": test_user.email,
        "password": "WrongPassword123!",
    }

    for _ in range(5):
        response = await client.post(
            "/api/v1/auth/login",
            json=login_data,
        )

        assert response.status_code == 401

    response = await client.post(
        "/api/v1/auth/login",
        json=login_data,
    )

    assert response.status_code == 429

    retry_after = int(response.headers["Retry-After"])

    assert retry_after > 0


