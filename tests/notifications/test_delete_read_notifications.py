import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from tests.utils.notification import create_notification


@pytest.mark.anyio
async def test_user_can_delete_all_read_notifications(
    client: AsyncClient,
    test_user: User,
    db_session: AsyncSession,
    user_headers: dict[str, str],
) -> None:
    notifications = [await create_notification(db_session, test_user) for _ in range(3)]

    for notification in notifications[:2]:
        mark_read_response = await client.patch(
            f"/api/v1/notifications/{notification.id}/read",
            headers=user_headers,
        )
        assert mark_read_response.status_code == 200

    response = await client.delete(
        "/api/v1/notifications?status=read",
        headers=user_headers,
    )

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.json()["message"] == ("Read notifications deleted successfully")

    list_response = await client.get(
        "/api/v1/notifications",
        headers=user_headers,
    )

    assert list_response.status_code == 200

    remaining_ids = {
        notification["id"] for notification in list_response.json()["data"]
    }

    assert str(notifications[2].id) in remaining_ids
    assert str(notifications[0].id) not in remaining_ids
    assert str(notifications[1].id) not in remaining_ids


@pytest.mark.anyio
async def test_delete_read_notifications_succeeds_when_none_exist(
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

    response = await client.delete(
        "/api/v1/notifications?status=read",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["success"] is True


@pytest.mark.anyio
async def test_delete_read_notifications_preserves_unread_notifications(
    client: AsyncClient,
    test_user: User,
    db_session: AsyncSession,
    user_headers: dict[str, str],
) -> None:
    notification = await create_notification(db_session, test_user)

    response = await client.delete(
        "/api/v1/notifications?status=read",
        headers=user_headers,
    )

    assert response.status_code == 200

    list_response = await client.get(
        "/api/v1/notifications",
        headers=user_headers,
    )

    assert list_response.status_code == 200

    remaining_ids = {item["id"] for item in list_response.json()["data"]}

    assert str(notification.id) in remaining_ids


@pytest.mark.anyio
async def test_delete_read_notifications_only_affects_current_user(
    client: AsyncClient,
    test_user: User,
    second_user: User,
    db_session: AsyncSession,
    user_headers: dict[str, str],
    second_user_headers: dict[str, str],
) -> None:
    notification = await create_notification(db_session, second_user)

    mark_read_response = await client.patch(
        f"/api/v1/notifications/{notification.id}/read",
        headers=second_user_headers,
    )

    assert mark_read_response.status_code == 200

    response = await client.delete(
        "/api/v1/notifications?status=read",
        headers=user_headers,
    )

    assert response.status_code == 200

    second_list_response = await client.get(
        "/api/v1/notifications",
        headers=second_user_headers,
    )

    assert second_list_response.status_code == 200

    remaining_ids = {item["id"] for item in second_list_response.json()["data"]}

    assert str(notification.id) in remaining_ids


@pytest.mark.anyio
async def test_unauthenticated_user_cannot_delete_read_notifications(
    client: AsyncClient,
) -> None:
    response = await client.delete(
        "/api/v1/notifications?status=read",
    )

    assert response.status_code == 401
