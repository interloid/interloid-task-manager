from httpx import AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


async def test_me_returns_current_user(
    client: AsyncClient,
    test_user,
) -> None:
    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user.email,
            "password": "StrongPassword123!",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["data"]["access_token"]

    response = await client.get(
        "/api/v1/users/me",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["success"] is True
    assert body["data"]["email"] == "testuser@example.com"
    assert body["data"]["first_name"] == "Test"
    assert body["data"]["last_name"] == "User"
    assert body["data"]["role"] == "user"
    assert body["data"]["is_active"] is True


async def test_me_without_token_returns_401(
    client: AsyncClient,
) -> None:
    response = await client.get(
        "/api/v1/users/me",
    )

    assert response.status_code == 401

    body = response.json()

    assert body["success"] is False
    assert body["error"]["code"] == "UNAUTHORIZED"

    assert response.headers["www-authenticate"] == "Bearer"


async def test_me_with_invalid_token_returns_401(
    client: AsyncClient,
) -> None:
    response = await client.get(
        "/api/v1/users/me",
        headers={
            "Authorization": "Bearer invalid-token",
        },
    )

    assert response.status_code == 401

    body = response.json()

    assert body["success"] is False
    assert body["error"]["code"] == "UNAUTHORIZED"

    assert response.headers["www-authenticate"] == "Bearer"


async def test_me_rejects_deactivated_user(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user,
) -> None:
    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user.email,
            "password": "StrongPassword123!",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["data"]["access_token"]

    await db_session.execute(
        update(User).where(User.id == test_user.id).values(is_active=False)
    )
    await db_session.commit()

    response = await client.get(
        "/api/v1/users/me",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
    )

    assert response.status_code == 401

    body = response.json()

    assert body["success"] is False
    assert body["error"]["code"] == "UNAUTHORIZED"
