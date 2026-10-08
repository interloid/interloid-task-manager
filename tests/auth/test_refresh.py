from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid6 import uuid7

from app.core.security import create_refresh_token, hash_refresh_token
from app.models.refresh_token import RefreshToken
from app.models.user import User


async def test_refresh_rotates_refresh_token(
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

    login_body = login_response.json()

    old_refresh_token = login_body["data"]["refresh_token"]

    refresh_response = await client.post(
        "/api/v1/auth/refresh",
        json={
            "refresh_token": old_refresh_token,
        },
    )

    assert refresh_response.status_code == 200

    refresh_body = refresh_response.json()

    new_access_token = refresh_body["data"]["access_token"]
    new_refresh_token = refresh_body["data"]["refresh_token"]

    assert new_access_token is not None
    assert new_refresh_token is not None
    assert new_refresh_token != old_refresh_token

    result = await db_session.execute(
        select(RefreshToken).where(
            RefreshToken.user_id == test_user.id,
        )
    )

    tokens = result.scalars().all()

    assert len(tokens) == 2


async def test_refresh_revokes_old_token_and_stores_new_token(
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

    old_refresh_token = login_response.json()["data"]["refresh_token"]

    refresh_response = await client.post(
        "/api/v1/auth/refresh",
        json={
            "refresh_token": old_refresh_token,
        },
    )

    assert refresh_response.status_code == 200

    new_refresh_token = refresh_response.json()["data"]["refresh_token"]

    old_hash = hash_refresh_token(old_refresh_token)
    new_hash = hash_refresh_token(new_refresh_token)

    result = await db_session.execute(
        select(RefreshToken).where(
            RefreshToken.user_id == test_user.id,
        )
    )

    tokens = result.scalars().all()

    old_db_token = next(token for token in tokens if token.token_hash == old_hash)

    new_db_token = next(token for token in tokens if token.token_hash == new_hash)

    assert old_db_token.revoked_at is not None
    assert new_db_token.revoked_at is None


async def test_reusing_rotated_refresh_token_returns_401(
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

    old_refresh_token = login_response.json()["data"]["refresh_token"]

    first_refresh = await client.post(
        "/api/v1/auth/refresh",
        json={
            "refresh_token": old_refresh_token,
        },
    )

    assert first_refresh.status_code == 200

    replay_response = await client.post(
        "/api/v1/auth/refresh",
        json={
            "refresh_token": old_refresh_token,
        },
    )

    assert replay_response.status_code == 401


async def test_refresh_with_invalid_token_returns_401(
    client: AsyncClient,
) -> None:
    response = await client.post(
        "/api/v1/auth/refresh",
        json={
            "refresh_token": "Invalid-refesh-token",
        },
    )

    assert response.status_code == 401


async def test_expired_refresh_token_returns_401(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user,
) -> None:
    refresh_token = create_refresh_token()

    stored_token = RefreshToken(
        token_hash=hash_refresh_token(refresh_token),
        user_id=test_user.id,
        expires_at=datetime.now(UTC) - timedelta(days=1),
        id=test_user.id,
        family_id=uuid7(),
    )

    db_session.add(stored_token)
    await db_session.commit()

    response = await client.post(
        "/api/v1/auth/refresh",
        json={
            "refresh_token": refresh_token,
        },
    )

    assert response.status_code == 401


async def test_inactive_user_cannot_refresh_token(
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

    test_user.is_active = False
    await db_session.commit()

    response = await client.post(
        "/api/v1/auth/refresh",
        json={
            "refresh_token": refresh_token,
        },
    )

    assert response.status_code == 401


async def test_refresh_token_with_missing_user_returns_401(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user,
) -> None:
    refresh_token = create_refresh_token()

    stored_token = RefreshToken(
        token_hash=hash_refresh_token(refresh_token),
        user_id=test_user.id,
        expires_at=datetime.now(UTC) + timedelta(days=1),
        id=test_user.id,
        family_id=uuid7(),
    )

    db_session.add(stored_token)
    await db_session.commit()

    await db_session.delete(test_user)
    await db_session.commit()

    response = await client.post(
        "/api/v1/auth/refresh",
        json={
            "refresh_token": refresh_token,
        },
    )

    assert response.status_code == 401


@pytest.mark.anyio
async def test_refresh_token_replay_revokes_only_compromised_family(
    client: AsyncClient,
    test_user: User,
) -> None:
    first_login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user.email,
            "password": "StrongPassword123!",
        },
    )

    assert first_login_response.status_code == 200

    first_refresh_token = first_login_response.json()["data"]["refresh_token"]

    first_refresh_response = await client.post(
        "/api/v1/auth/refresh",
        json={
            "refresh_token": first_refresh_token,
        },
    )

    assert first_refresh_response.status_code == 200

    second_refresh_token = first_refresh_response.json()["data"]["refresh_token"]

    second_login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user.email,
            "password": "StrongPassword123!",
        },
    )

    assert second_login_response.status_code == 200

    other_family_refresh_token = second_login_response.json()["data"]["refresh_token"]

    replay_response = await client.post(
        "/api/v1/auth/refresh",
        json={
            "refresh_token": first_refresh_token,
        },
    )

    assert replay_response.status_code == 401

    compromised_family_response = await client.post(
        "/api/v1/auth/refresh",
        json={
            "refresh_token": second_refresh_token,
        },
    )

    assert compromised_family_response.status_code == 401

    other_family_response = await client.post(
        "/api/v1/auth/refresh",
        json={
            "refresh_token": other_family_refresh_token,
        },
    )

    assert other_family_response.status_code == 200
