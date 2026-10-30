from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from tests.utils.notification import create_notification


@pytest.mark.anyio
async def test_user_can_mark_own_notification_as_read(
    client: AsyncClient,
    test_user: User,
    db_session: AsyncSession,
    user_headers: dict[str, str],
) -> None:
    notification = await create_notification(db_session, test_user)

    response = await client.patch(
        f"/api/v1/notifications/{notification.id}/read",
        headers=user_headers,
    )

    assert response.status_code == 200

    body = response.json()

    assert body["success"] is True
    assert body["message"] == "Notification marked as read successfully"
    assert body["data"]["id"] == str(notification.id)
    assert body["data"]["status"] == "read"


@pytest.mark.anyio
async def test_mark_nonexistent_notification_as_read_returns_404(
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
    headers = {"Authorization": f"Bearer {access_token}"}

    response = await client.patch(
        f"/api/v1/notifications/{uuid4()}/read",
        headers=headers,
    )

    assert response.status_code == 404


@pytest.mark.anyio
async def test_user_cannot_mark_another_users_notification_as_read(
    client: AsyncClient,
    test_user: User,
    second_user: User,
    db_session: AsyncSession,
    second_user_headers: dict[str, str],
) -> None:
    notification = await create_notification(db_session, test_user)

    response = await client.patch(
        f"/api/v1/notifications/{notification.id}/read",
        headers=second_user_headers,
    )

    assert response.status_code == 404


@pytest.mark.anyio
async def test_unauthenticated_user_cannot_mark_notification_as_read(
    client: AsyncClient,
) -> None:
    response = await client.patch(
        f"/api/v1/notifications/{uuid4()}/read",
    )

    assert response.status_code == 401


@pytest.mark.anyio
async def test_mark_already_read_notification_as_read(
    client: AsyncClient,
    test_user: User,
    db_session: AsyncSession,
    user_headers: dict[str, str],
) -> None:
    notification = await create_notification(db_session, test_user)

    first_response = await client.patch(
        f"/api/v1/notifications/{notification.id}/read",
        headers=user_headers,
    )

    assert first_response.status_code == 200
    assert first_response.json()["data"]["status"] == "read"

    second_response = await client.patch(
        f"/api/v1/notifications/{notification.id}/read",
        headers=user_headers,
    )

    assert second_response.status_code == 200
    assert second_response.json()["data"]["status"] == "read"
