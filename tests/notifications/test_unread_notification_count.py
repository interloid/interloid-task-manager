import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from tests.utils.notification import create_notification


@pytest.mark.anyio
async def test_user_can_get_unread_notification_count(
    client: AsyncClient,
    test_user: User,
    db_session: AsyncSession,
    user_headers: dict[str, str],
) -> None:
    for _ in range(2):
        await create_notification(db_session, test_user)

    response = await client.get(
        "/api/v1/notifications/unread-count",
        headers=user_headers,
    )

    assert response.status_code == 200

    body = response.json()
    assert body["success"] is True
    assert body["message"] == "Unread notification count retrieved successfully"
    assert body["data"]["unread_count"] == 2


@pytest.mark.anyio
async def test_unread_count_is_zero_when_no_unread_notifications(
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

    response = await client.get(
        "/api/v1/notifications/unread-count",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["data"]["unread_count"] == 0


@pytest.mark.anyio
async def test_unread_count_excludes_read_notifications(
    client: AsyncClient,
    test_user: User,
    db_session: AsyncSession,
    user_headers: dict[str, str],
) -> None:
    notification = await create_notification(db_session, test_user)

    mark_read_response = await client.patch(
        f"/api/v1/notifications/{notification.id}/read",
        headers=user_headers,
    )

    assert mark_read_response.status_code == 200

    response = await client.get(
        "/api/v1/notifications/unread-count",
        headers=user_headers,
    )

    assert response.status_code == 200
    assert response.json()["data"]["unread_count"] == 0


@pytest.mark.anyio
async def test_unread_count_includes_only_current_users_notifications(
    client: AsyncClient,
    test_user: User,
    second_user: User,
    db_session: AsyncSession,
    user_headers: dict[str, str],
    second_user_headers: dict[str, str],
) -> None:
    await create_notification(db_session, second_user)

    response = await client.get(
        "/api/v1/notifications/unread-count",
        headers=user_headers,
    )

    assert response.status_code == 200
    assert response.json()["data"]["unread_count"] == 0

    second_response = await client.get(
        "/api/v1/notifications/unread-count",
        headers=second_user_headers,
    )

    assert second_response.status_code == 200
    assert second_response.json()["data"]["unread_count"] == 1


@pytest.mark.anyio
async def test_unauthenticated_user_cannot_get_unread_count(
    client: AsyncClient,
) -> None:
    response = await client.get(
        "/api/v1/notifications/unread-count",
    )

    assert response.status_code == 401
