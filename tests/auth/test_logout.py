import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_refresh_token
from app.models.refresh_token import RefreshToken
from app.models.user import User


async def test_logout_revokes_refresh_token(
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

    refresh_token = login_response.json()["data"]["refresh_token"]

    logout_response = await client.post(
        "/api/v1/auth/logout",
        json={
            "refresh_token": refresh_token,
        },
    )

    assert logout_response.status_code == 200

    token_hash = hash_refresh_token(refresh_token)

    result = await db_session.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
        )
    )

    stored_token = result.scalar_one_or_none()

    assert stored_token is not None
    assert stored_token.revoked_at is not None


async def test_logout_already_revoked_token_returns_200(
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

    refresh_token = login_response.json()["data"]["refresh_token"]

    first_logout = await client.post(
        "/api/v1/auth/logout",
        json={
            "refresh_token": refresh_token,
        },
    )

    assert first_logout.status_code == 200

    second_logout = await client.post(
        "/api/v1/auth/logout",
        json={
            "refresh_token": refresh_token,
        },
    )

    assert second_logout.status_code == 200


async def test_logout_invalid_refresh_token_returns_401(
    client: AsyncClient,
) -> None:
    response = await client.post(
        "/api/v1/auth/logout",
        json={
            "refresh_token": "this-token-does-not-exist",
        },
    )

    assert response.status_code == 401

    body = response.json()

    assert body["success"] is False
    assert body["error"]["code"] == "INVALID_REFRESH_TOKEN"


async def test_logged_out_refresh_token_cannot_be_refreshed(
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

    refresh_token = login_response.json()["data"]["refresh_token"]

    logout_response = await client.post(
        "/api/v1/auth/logout",
        json={
            "refresh_token": refresh_token,
        },
    )

    assert logout_response.status_code == 200

    refresh_response = await client.post(
        "/api/v1/auth/refresh",
        json={
            "refresh_token": refresh_token,
        },
    )

    assert refresh_response.status_code == 401


@pytest.mark.anyio
async def test_logout_all_revokes_all_refresh_tokens(
    client: AsyncClient,
    test_user: User,
) -> None:
    first_login = await client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user.email,
            "password": "StrongPassword123!",
        },
    )

    assert first_login.status_code == 200

    first_refresh_token = first_login.json()["data"]["refresh_token"]

    second_login = await client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user.email,
            "password": "StrongPassword123!",
        },
    )

    assert second_login.status_code == 200

    second_access_token = second_login.json()["data"]["access_token"]

    second_refresh_token = second_login.json()["data"]["refresh_token"]

    logout_all_response = await client.post(
        "/api/v1/auth/logout-all",
        headers={
            "Authorization": f"Bearer {second_access_token}",
        },
    )

    assert logout_all_response.status_code == 200

    first_refresh_response = await client.post(
        "/api/v1/auth/refresh",
        json={
            "refresh_token": first_refresh_token,
        },
    )

    assert first_refresh_response.status_code == 401

    second_refresh_response = await client.post(
        "/api/v1/auth/refresh",
        json={
            "refresh_token": second_refresh_token,
        },
    )

    assert second_refresh_response.status_code == 401


@pytest.mark.anyio
async def test_logout_all_requires_authentication(
    client: AsyncClient,
) -> None:
    response = await client.post(
        "/api/v1/auth/logout-all",
    )

    assert response.status_code == 401


@pytest.mark.anyio
async def test_logout_invalidates_access_token(
    client: AsyncClient,
    test_user: User,
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
    refresh_token = login_response.json()["data"]["refresh_token"]

    headers = {
        "Authorization": f"Bearer {access_token}",
    }

    logout_response = await client.post(
        "/api/v1/auth/logout",
        json={
            "refresh_token": refresh_token,
        },
    )

    assert logout_response.status_code == 200

    me_response = await client.get(
        "/api/v1/users/me",
        headers=headers,
    )

    assert me_response.status_code == 401


@pytest.mark.anyio
async def test_logout_all_invalidates_existing_access_tokens(
    client: AsyncClient,
    test_user: User,
) -> None:
    first_login = await client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user.email,
            "password": "StrongPassword123!",
        },
    )

    second_login = await client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user.email,
            "password": "StrongPassword123!",
        },
    )

    first_access_token = first_login.json()["data"]["access_token"]
    second_access_token = second_login.json()["data"]["access_token"]

    logout_all_response = await client.post(
        "/api/v1/auth/logout-all",
        headers={
            "Authorization": f"Bearer {first_access_token}",
        },
    )

    assert logout_all_response.status_code == 200

    for access_token in [
        first_access_token,
        second_access_token,
    ]:
        response = await client.get(
            "/api/v1/users/me",
            headers={
                "Authorization": f"Bearer {access_token}",
            },
        )

        assert response.status_code == 401
