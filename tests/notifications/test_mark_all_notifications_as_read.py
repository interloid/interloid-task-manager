import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums.notification import NotificationStatus
from app.models.user import User
from tests.utils.notification import create_notification


@pytest.mark.anyio
async def test_user_can_mark_all_notifications_as_read(
    client: AsyncClient,
    test_user: User,
    db_session: AsyncSession,
    user_headers: dict[str, str],
) -> None:
    for _ in range(3):
        await create_notification(db_session, test_user)

    response = await client.patch(
        "/api/v1/notifications/read-all",
        headers=user_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["message"] == "All notifications marked as read successfully"
    assert body["data"]["updated_count"] == 3

    count_response = await client.get(
        "/api/v1/notifications/unread-count",
        headers=user_headers,
    )

    assert count_response.status_code == 200
    assert count_response.json()["data"]["unread_count"] == 0


@pytest.mark.anyio
async def test_mark_all_as_read_when_no_unread_notifications(
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
    headers = {
        "Authorization": (f"Bearer {login_response.json()['data']['access_token']}"),
    }

    response = await client.patch(
        "/api/v1/notifications/read-all",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["data"]["updated_count"] == 0


@pytest.mark.anyio
async def test_mark_all_as_read_does_not_change_other_users_notifications(
    client: AsyncClient,
    test_user: User,
    second_user: User,
    db_session: AsyncSession,
    user_headers: dict[str, str],
    second_user_headers: dict[str, str],
) -> None:
    await create_notification(db_session, second_user)

    response = await client.patch(
        "/api/v1/notifications/read-all",
        headers=user_headers,
    )

    assert response.status_code == 200
    assert response.json()["data"]["updated_count"] == 0

    second_count_response = await client.get(
        "/api/v1/notifications/unread-count",
        headers=second_user_headers,
    )

    assert second_count_response.status_code == 200
    assert second_count_response.json()["data"]["unread_count"] == 1


@pytest.mark.anyio
async def test_mark_all_as_read_preserves_existing_read_notifications(
    client: AsyncClient,
    test_user: User,
    db_session: AsyncSession,
    user_headers: dict[str, str],
) -> None:
    notification = await create_notification(
        db_session,
        test_user,
        status=NotificationStatus.READ,
    )

    response = await client.patch(
        "/api/v1/notifications/read-all",
        headers=user_headers,
    )

    assert response.status_code == 200
    assert response.json()["data"]["updated_count"] == 0

    list_response = await client.get(
        "/api/v1/notifications",
        headers=user_headers,
    )

    assert list_response.status_code == 200

    notifications = list_response.json()["data"]
    matching_notification = next(
        item for item in notifications if item["id"] == str(notification.id)
    )
    assert matching_notification["status"] == "read"


@pytest.mark.anyio
async def test_unauthenticated_user_cannot_mark_all_notifications_as_read(
    client: AsyncClient,
) -> None:
    response = await client.patch(
        "/api/v1/notifications/read-all",
    )

    assert response.status_code == 401
