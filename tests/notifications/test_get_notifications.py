import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums.notification import NotificationStatus
from app.models import User
from tests.utils.notification import create_notification


@pytest.mark.anyio
async def test_user_can_get_own_notifications(
    test_user: User,
    client: AsyncClient,
    user_headers: dict[str, str],
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

    headers = {
        "Authorization": f"Bearer {access_token}",
    }

    await create_notification(db_session, test_user)

    response = await client.get(
        "/api/v1/notifications?page=1&page_size=10",
        headers=headers,
    )

    assert response.status_code == 200


@pytest.mark.anyio
async def test_user_cannot_get_another_users_notifications(
    client: AsyncClient,
    test_user: User,
    second_user: User,
    db_session: AsyncSession,
    second_user_headers: dict[str, str],
) -> None:
    await create_notification(db_session, test_user)

    response = await client.get(
        "/api/v1/notifications",
        headers=second_user_headers,
    )

    assert response.status_code == 200

    body = response.json()

    assert body["success"] is True
    assert body["data"] == []
    assert body["pagination"]["total"] == 0


@pytest.mark.anyio
async def test_user_gets_empty_notifications(
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
    headers = {"Authorization": f"Bearer {access_token}"}

    response = await client.get(
        "/api/v1/notifications",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["data"] == []
    assert response.json()["pagination"]["total"] == 0


@pytest.mark.anyio
async def test_unauthenticated_user_cannot_get_notifications(
    client: AsyncClient,
) -> None:
    response = await client.get("/api/v1/notifications")

    assert response.status_code == 401


@pytest.mark.anyio
async def test_user_can_filter_unread_notifications(
    test_user: User,
    client: AsyncClient,
    db_session: AsyncSession,
    user_headers: dict[str, str],
) -> None:
    await create_notification(
        db_session,
        test_user,
        status=NotificationStatus.READ,
    )
    unread_notification = await create_notification(
        db_session,
        test_user,
        status=NotificationStatus.UNREAD,
    )

    response = await client.get(
        "/api/v1/notifications?is_read=false",
        headers=user_headers,
    )

    assert response.status_code == 200

    body = response.json()
    notifications = body["data"]

    assert len(notifications) == 1
    assert notifications[0]["id"] == str(unread_notification.id)
    assert notifications[0]["status"] == "unread"
    assert body["pagination"]["total"] == 1


@pytest.mark.anyio
async def test_user_can_filter_read_notifications(
    test_user: User,
    client: AsyncClient,
    db_session: AsyncSession,
    user_headers: dict[str, str],
) -> None:
    read_notification = await create_notification(
        db_session,
        test_user,
        status=NotificationStatus.READ,
    )
    await create_notification(
        db_session,
        test_user,
        status=NotificationStatus.UNREAD,
    )

    response = await client.get(
        "/api/v1/notifications?is_read=true",
        headers=user_headers,
    )

    assert response.status_code == 200

    body = response.json()
    notifications = body["data"]

    assert len(notifications) == 1
    assert notifications[0]["id"] == str(read_notification.id)
    assert notifications[0]["status"] == "read"
    assert body["pagination"]["total"] == 1


@pytest.mark.anyio
async def test_user_gets_all_notifications_without_read_filter(
    test_user: User,
    client: AsyncClient,
    db_session: AsyncSession,
    user_headers: dict[str, str],
) -> None:
    await create_notification(
        db_session,
        test_user,
        status=NotificationStatus.READ,
    )
    await create_notification(
        db_session,
        test_user,
        status=NotificationStatus.UNREAD,
    )

    response = await client.get(
        "/api/v1/notifications?page=1&page_size=10",
        headers=user_headers,
    )

    assert response.status_code == 200

    body = response.json()
    notifications = body["data"]

    assert len(notifications) == 2
    assert body["pagination"]["total"] == 2

    statuses = {notification["status"] for notification in notifications}
    assert statuses == {"read", "unread"}


@pytest.mark.anyio
async def test_filtered_notifications_have_correct_pagination(
    test_user: User,
    client: AsyncClient,
    db_session: AsyncSession,
    user_headers: dict[str, str],
) -> None:
    for index in range(5):
        status = NotificationStatus.READ if index < 3 else NotificationStatus.UNREAD

        await create_notification(
            db_session,
            test_user,
            status=status,
        )

    response = await client.get(
        "/api/v1/notifications?is_read=false&page=1&page_size=1",
        headers=user_headers,
    )

    assert response.status_code == 200

    body = response.json()

    assert len(body["data"]) == 1
    assert body["pagination"]["page"] == 1
    assert body["pagination"]["page_size"] == 1
    assert body["pagination"]["total"] == 2
    assert body["pagination"]["total_pages"] == 2


@pytest.mark.anyio
async def test_read_filter_only_returns_current_users_notifications(
    test_user: User,
    second_user: User,
    client: AsyncClient,
    db_session: AsyncSession,
    user_headers: dict[str, str],
) -> None:
    first_notification = await create_notification(
        db_session,
        test_user,
    )

    await create_notification(
        db_session,
        second_user,
    )

    response = await client.get(
        "/api/v1/notifications?is_read=false",
        headers=user_headers,
    )

    assert response.status_code == 200

    body = response.json()
    notifications = body["data"]

    assert len(notifications) == 1
    assert notifications[0]["id"] == str(first_notification.id)
    assert notifications[0]["user_id"] == str(test_user.id)
    assert body["pagination"]["total"] == 1


@pytest.mark.anyio
async def test_notifications_reject_invalid_is_read_value(
    test_user: User,
    client: AsyncClient,
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
        "/api/v1/notifications?is_read=invalid",
        headers=headers,
    )

    assert response.status_code == 422
