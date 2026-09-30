import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.refresh_token import RefreshToken
from app.models.user import User


async def test_change_password_success(
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

    response = await client.patch(
        "/api/v1/users/me/password",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
        json={
            "current_password": "StrongPassword123!",
            "new_password": "NewStrongPassword123!",
        },
    )

    assert response.status_code == 200


async def test_old_password_fails_after_password_change(
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

    access_token = login_response.json()["data"]["access_token"]

    change_response = await client.patch(
        "/api/v1/users/me/password",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
        json={
            "current_password": "StrongPassword123!",
            "new_password": "NewStrongPassword123!",
        },
    )

    assert change_response.status_code == 200

    old_password_login = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "testuser@example.com",
            "password": "StrongPassword123!",
        },
    )

    assert old_password_login.status_code == 401


async def test_new_password_works_after_password_change(
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

    access_token = login_response.json()["data"]["access_token"]

    change_response = await client.patch(
        "/api/v1/users/me/password",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
        json={
            "current_password": "StrongPassword123!",
            "new_password": "NewStrongPassword123!",
        },
    )

    assert change_response.status_code == 200

    new_password_login = await client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user.email,
            "password": "NewStrongPassword123!",
        },
    )

    assert new_password_login.status_code == 200


async def test_change_password_wrong_current_password_returns_401(
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

    access_token = login_response.json()["data"]["access_token"]

    response = await client.patch(
        "/api/v1/users/me/password",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
        json={
            "current_password": "WrongPassword123!",
            "new_password": "NewStrongPassword123!",
        },
    )

    assert response.status_code == 401


async def test_change_password_revokes_all_refresh_tokens(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user,
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

    assert first_login.status_code == 200
    assert second_login.status_code == 200

    access_token = first_login.json()["data"]["access_token"]

    result = await db_session.execute(
        select(RefreshToken).where(
            RefreshToken.user_id == test_user.id,
        )
    )

    tokens_before = result.scalars().all()

    assert len(tokens_before) == 2

    response = await client.patch(
        "/api/v1/users/me/password",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
        json={
            "current_password": "StrongPassword123!",
            "new_password": "NewStrongPassword123!",
        },
    )

    assert response.status_code == 200

    result = await db_session.execute(
        select(RefreshToken)
        .where(
            RefreshToken.user_id == test_user.id,
        )
        .execution_options(
            populate_existing=True,
        )
    )

    tokens_after = result.scalars().all()

    assert len(tokens_after) == 2

    for token in tokens_after:
        assert token.revoked_at is not None


async def test_change_password_with_same_password_returns_422(
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

    response = await client.patch(
        "/api/v1/users/me/password",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
        json={
            "current_password": "StrongPassword123!",
            "new_password": "StrongPassword123!",
        },
    )

    assert response.status_code == 422

    body = response.json()

    assert body["success"] is False
    assert body["message"] == (
        "New password must be different from the current password"
    )
    assert body["error"]["code"] == "SAME_PASSWORD"


@pytest.mark.anyio
async def test_old_access_token_invalid_after_password_change(
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

    headers = {
        "Authorization": f"Bearer {access_token}",
    }

    change_password_response = await client.patch(
        "/api/v1/users/me/password",
        headers=headers,
        json={
            "current_password": "StrongPassword123!",
            "new_password": "NewStrongPassword123!",
        },
    )

    assert change_password_response.status_code == 200

    me_response = await client.get(
        "/api/v1/users/me",
        headers=headers,
    )

    assert me_response.status_code == 401


@pytest.mark.anyio
async def test_new_access_token_valid_after_password_change(
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

    old_access_token = login_response.json()["data"]["access_token"]

    old_headers = {
        "Authorization": f"Bearer {old_access_token}",
    }

    change_password_response = await client.patch(
        "/api/v1/users/me/password",
        headers=old_headers,
        json={
            "current_password": "StrongPassword123!",
            "new_password": "NewStrongPassword123!",
        },
    )

    assert change_password_response.status_code == 200

    new_login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user.email,
            "password": "NewStrongPassword123!",
        },
    )

    assert new_login_response.status_code == 200

    new_access_token = new_login_response.json()["data"]["access_token"]

    new_headers = {
        "Authorization": f"Bearer {new_access_token}",
    }

    me_response = await client.get(
        "/api/v1/users/me",
        headers=new_headers,
    )

    assert me_response.status_code == 200
