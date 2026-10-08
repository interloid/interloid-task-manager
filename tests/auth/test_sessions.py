from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from uuid6 import uuid7

from app.core.security import decode_token, hash_refresh_token
from app.models.refresh_token import RefreshToken
from app.models.user import User


@pytest.mark.anyio
async def test_get_sessions_returns_current_session(
    client: AsyncClient,
    test_user: User,
) -> None:
    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user.email,
            "password": "StrongPassword123!",
        },
        headers={
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 "
                "Chrome/150.0.0.0 Safari/537.36"
            ),
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["data"]["access_token"]

    response = await client.get(
        "/api/v1/auth/sessions",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["success"] is True
    assert body["message"] == "Active sessions fetched successfully"

    assert body["total"] == 1

    sessions = body["data"]

    assert len(sessions) == 1
    assert sessions[0]["is_current"] is True
    assert sessions[0]["created_at"] is not None
    assert sessions[0]["expires_at"] is not None


@pytest.mark.anyio
async def test_current_session_id_matches_access_token_sid(
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

    payload = decode_token(access_token)
    session_id = payload["sid"]

    response = await client.get(
        "/api/v1/auth/sessions",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
    )

    assert response.status_code == 200

    sessions = response.json()["data"]

    assert len(sessions) == 1
    assert sessions[0]["id"] == session_id
    assert sessions[0]["is_current"] is True


@pytest.mark.anyio
async def test_get_sessions_returns_multiple_active_sessions(
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

    second_login = await client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user.email,
            "password": "StrongPassword123!",
        },
    )

    assert second_login.status_code == 200

    second_access_token = second_login.json()["data"]["access_token"]

    response = await client.get(
        "/api/v1/auth/sessions",
        headers={
            "Authorization": (f"Bearer {second_access_token}"),
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["total"] == 2

    sessions = body["data"]

    assert len(sessions) == 2

    current_sessions = [
        session for session in sessions if session["is_current"] is True
    ]

    assert len(current_sessions) == 1


@pytest.mark.anyio
async def test_get_sessions_excludes_revoked_sessions(
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

    logout_response = await client.post(
        "/api/v1/auth/logout",
        json={
            "refresh_token": first_refresh_token,
        },
    )

    assert logout_response.status_code == 200

    response = await client.get(
        "/api/v1/auth/sessions",
        headers={
            "Authorization": (f"Bearer {second_access_token}"),
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["total"] == 1
    assert len(body["data"]) == 1
    assert body["data"][0]["is_current"] is True


@pytest.mark.anyio
async def test_get_sessions_excludes_expired_sessions(
    client: AsyncClient,
    test_user: User,
    db_session: AsyncSession,
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

    expired_raw_token = "expired-session-token"

    expired_session = RefreshToken(
        token_hash=hash_refresh_token(expired_raw_token),
        expires_at=datetime.now(UTC) - timedelta(days=1),
        user_id=test_user.id,
        family_id=uuid7(),
        browser="Chrome",
        os="Ubuntu",
    )

    db_session.add(expired_session)
    await db_session.commit()

    response = await client.get(
        "/api/v1/auth/sessions",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["total"] == 1
    assert len(body["data"]) == 1
    assert body["data"][0]["is_current"] is True


@pytest.mark.anyio
async def test_get_sessions_without_access_token_returns_401(
    client: AsyncClient,
) -> None:
    response = await client.get(
        "/api/v1/auth/sessions",
    )

    assert response.status_code == 401


@pytest.mark.anyio
async def test_revoke_single_session(
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

    first_access_token = first_login.json()["data"]["access_token"]

    first_refresh_token = first_login.json()["data"]["refresh_token"]

    second_login = await client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user.email,
            "password": "StrongPassword123!",
        },
    )

    assert second_login.status_code == 200

    second_refresh_token = second_login.json()["data"]["refresh_token"]

    sessions_response = await client.get(
        "/api/v1/auth/sessions",
        headers={
            "Authorization": f"Bearer {first_access_token}",
        },
    )

    assert sessions_response.status_code == 200

    sessions = sessions_response.json()["data"]

    second_session = next(
        session for session in sessions if session["is_current"] is False
    )

    revoke_response = await client.delete(
        f"/api/v1/auth/sessions/{second_session['id']}",
        headers={
            "Authorization": f"Bearer {first_access_token}",
        },
    )

    assert revoke_response.status_code == 200

    revoked_refresh_response = await client.post(
        "/api/v1/auth/refresh",
        json={
            "refresh_token": second_refresh_token,
        },
    )

    assert revoked_refresh_response.status_code == 401

    current_refresh_response = await client.post(
        "/api/v1/auth/refresh",
        json={
            "refresh_token": first_refresh_token,
        },
    )

    assert current_refresh_response.status_code == 200


@pytest.mark.anyio
async def test_revoke_nonexistent_session_returns_404(
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

    access_token = login_response.json()["data"]["access_token"]

    response = await client.delete(
        f"/api/v1/auth/sessions/{uuid7()}",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
    )

    assert response.status_code == 404


@pytest.mark.anyio
async def test_revoke_session_requires_authentication(
    client: AsyncClient,
) -> None:
    response = await client.delete(
        f"/api/v1/auth/sessions/{uuid7()}",
    )

    assert response.status_code == 401


@pytest.mark.anyio
async def test_revoked_session_access_token_returns_401(
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

    sessions_response = await client.get(
        "/api/v1/auth/sessions",
        headers=headers,
    )

    assert sessions_response.status_code == 200

    session_id = sessions_response.json()["data"][0]["id"]

    revoke_response = await client.delete(
        f"/api/v1/auth/sessions/{session_id}",
        headers=headers,
    )

    assert revoke_response.status_code == 200

    me_response = await client.get(
        "/api/v1/users/me",
        headers=headers,
    )

    assert me_response.status_code == 401
