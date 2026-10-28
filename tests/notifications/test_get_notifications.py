import pytest
from httpx import AsyncClient

from app.models import User


@pytest.mark.anyio
async def test_user_can_get_own_notifications(
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

    headers = {
        "Authorization": f"Bearer {access_token}",
    }

    for index in range(2):
        create_response = await client.post(
            "/api/v1/notifications",
            json={
                "type": "task_commented",
                "title": f"Notification {index + 1}",
                "message": f"Test notification message {index + 1}",
            },
            headers=headers,
        )

        assert create_response.status_code == 201

    response = await client.get(
        "/api/v1/notifications?page=1&page_size=10",
        headers=headers,
    )

    assert response.status_code == 200

    body = response.json()

    assert body["success"] is True
    assert body["message"] == "Notifications retrieved successfully"
    notifications = body["data"]
    pagination = body["pagination"]

    assert len(notifications) == 2
    assert all(
        notification["user_id"] == str(test_user.id) for notification in notifications
    )

    assert pagination["page"] == 1
    assert pagination["page_size"] == 10
    assert pagination["total"] == 2
    assert pagination["total_pages"] == 1


@pytest.mark.anyio
async def test_user_cannot_get_another_users_notifications(
    client: AsyncClient,
    test_user: User,
    second_user: User,
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
    create_response = await client.post(
        "/api/v1/notifications",
        json={
            "type": "task_commented",
            "title": "First user's notification",
            "message": "This notification belongs to the first user.",
        },
        headers=headers,
    )

    assert create_response.status_code == 201

    second_login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": second_user.email,
            "password": "Test1234",
        },
    )

    assert second_login_response.status_code == 200

    second_access_token = second_login_response.json()["data"]["access_token"]
    second_headers = {
        "Authorization": f"Bearer {second_access_token}",
    }

    response = await client.get(
        "/api/v1/notifications",
        headers=second_headers,
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

    notification_ids = []

    for index in range(2):
        create_response = await client.post(
            "/api/v1/notifications",
            json={
                "type": "task_commented",
                "title": f"Notification {index + 1}",
                "message": f"Test notification message {index + 1}",
            },
            headers=headers,
        )

        assert create_response.status_code == 201
        notification_ids.append(create_response.json()["data"]["id"])

    mark_read_response = await client.patch(
        f"/api/v1/notifications/{notification_ids[0]}/read",
        headers=headers,
    )

    assert mark_read_response.status_code == 200

    response = await client.get(
        "/api/v1/notifications?is_read=false",
        headers=headers,
    )

    assert response.status_code == 200

    body = response.json()
    notifications = body["data"]

    assert len(notifications) == 1
    assert notifications[0]["id"] == notification_ids[1]
    assert notifications[0]["status"] == "unread"
    assert body["pagination"]["total"] == 1


@pytest.mark.anyio
async def test_user_can_filter_read_notifications(
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

    notification_ids = []

    for index in range(2):
        create_response = await client.post(
            "/api/v1/notifications",
            json={
                "type": "task_commented",
                "title": f"Notification {index + 1}",
                "message": f"Test notification message {index + 1}",
            },
            headers=headers,
        )

        assert create_response.status_code == 201
        notification_ids.append(create_response.json()["data"]["id"])

    mark_read_response = await client.patch(
        f"/api/v1/notifications/{notification_ids[0]}/read",
        headers=headers,
    )

    assert mark_read_response.status_code == 200

    response = await client.get(
        "/api/v1/notifications?is_read=true",
        headers=headers,
    )

    assert response.status_code == 200

    body = response.json()
    notifications = body["data"]

    assert len(notifications) == 1
    assert notifications[0]["id"] == notification_ids[0]
    assert notifications[0]["status"] == "read"
    assert body["pagination"]["total"] == 1


@pytest.mark.anyio
async def test_user_gets_all_notifications_without_read_filter(
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

    notification_ids = []

    for index in range(2):
        create_response = await client.post(
            "/api/v1/notifications",
            json={
                "type": "task_commented",
                "title": f"Notification {index + 1}",
                "message": f"Test notification message {index + 1}",
            },
            headers=headers,
        )

        assert create_response.status_code == 201
        notification_ids.append(create_response.json()["data"]["id"])

    mark_read_response = await client.patch(
        f"/api/v1/notifications/{notification_ids[0]}/read",
        headers=headers,
    )

    assert mark_read_response.status_code == 200

    response = await client.get(
        "/api/v1/notifications?page=1&page_size=10",
        headers=headers,
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

    notification_ids = []

    for index in range(5):
        create_response = await client.post(
            "/api/v1/notifications",
            json={
                "type": "task_commented",
                "title": f"Notification {index + 1}",
                "message": f"Test notification message {index + 1}",
            },
            headers=headers,
        )

        assert create_response.status_code == 201
        notification_ids.append(create_response.json()["data"]["id"])

    for notification_id in notification_ids[:3]:
        mark_read_response = await client.patch(
            f"/api/v1/notifications/{notification_id}/read",
            headers=headers,
        )
        assert mark_read_response.status_code == 200
    response = await client.get(
        "/api/v1/notifications?is_read=false&page=1&page_size=1",
        headers=headers,
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

    first_response = await client.post(
        "/api/v1/notifications",
        json={
            "type": "task_commented",
            "title": "First user's notification",
            "message": "Notification belonging to the first user",
        },
        headers=headers,
    )

    assert first_response.status_code == 201
    first_notification_id = first_response.json()["data"]["id"]

    second_login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": second_user.email,
            "password": "Test1234",
        },
    )

    assert second_login_response.status_code == 200

    second_access_token = second_login_response.json()["data"]["access_token"]
    second_headers = {
        "Authorization": f"Bearer {second_access_token}",
    }

    second_response = await client.post(
        "/api/v1/notifications",
        json={
            "type": "task_commented",
            "title": "Second user's notification",
            "message": "Notification belonging to the second user",
        },
        headers=second_headers,
    )

    assert second_response.status_code == 201

    response = await client.get(
        "/api/v1/notifications?is_read=false",
        headers=headers,
    )

    assert response.status_code == 200

    body = response.json()
    notifications = body["data"]

    assert len(notifications) == 1
    assert notifications[0]["id"] == first_notification_id
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
