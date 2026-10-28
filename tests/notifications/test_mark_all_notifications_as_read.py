import pytest
from httpx import AsyncClient

from app.models.user import User


@pytest.mark.anyio
async def test_user_can_mark_all_notifications_as_read(
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

    for index in range(3):
        create_response = await client.post(
            "/api/v1/notifications",
            json={
                "type": "task_commented",
                "title": f"Notification {index + 1}",
                "message": f"Test notification {index + 1}",
            },
            headers=headers,
        )
        assert create_response.status_code == 201

    response = await client.patch(
        "/api/v1/notifications/read-all",
        headers=headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["message"] == ("All notifications marked as read successfully")
    assert body["data"]["updated_count"] == 3

    count_response = await client.get(
        "/api/v1/notifications/unread-count",
        headers=headers,
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
) -> None:
    first_login = await client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user.email,
            "password": "StrongPassword123!",
        },
    )
    assert first_login.status_code == 200
    first_headers = {
        "Authorization": (f"Bearer {first_login.json()['data']['access_token']}"),
    }

    second_login = await client.post(
        "/api/v1/auth/login",
        json={
            "email": second_user.email,
            "password": "Test1234",
        },
    )
    assert second_login.status_code == 200
    second_headers = {
        "Authorization": (f"Bearer {second_login.json()['data']['access_token']}"),
    }

    create_response = await client.post(
        "/api/v1/notifications",
        json={
            "type": "task_commented",
            "title": "Second user's notification",
            "message": "This notification belongs to the second user.",
        },
        headers=second_headers,
    )
    assert create_response.status_code == 201

    response = await client.patch(
        "/api/v1/notifications/read-all",
        headers=first_headers,
    )
    assert response.status_code == 200
    assert response.json()["data"]["updated_count"] == 0

    second_count_response = await client.get(
        "/api/v1/notifications/unread-count",
        headers=second_headers,
    )
    assert second_count_response.status_code == 200
    assert second_count_response.json()["data"]["unread_count"] == 1


@pytest.mark.anyio
async def test_mark_all_as_read_preserves_existing_read_notifications(
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

    create_response = await client.post(
        "/api/v1/notifications",
        json={
            "type": "task_commented",
            "title": "Already read",
            "message": "This notification will be read first.",
        },
        headers=headers,
    )
    assert create_response.status_code == 201
    notification_id = create_response.json()["data"]["id"]

    mark_read_response = await client.patch(
        f"/api/v1/notifications/{notification_id}/read",
        headers=headers,
    )
    assert mark_read_response.status_code == 200

    response = await client.patch(
        "/api/v1/notifications/read-all",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["data"]["updated_count"] == 0

    list_response = await client.get(
        "/api/v1/notifications",
        headers=headers,
    )
    assert list_response.status_code == 200

    notifications = list_response.json()["data"]
    notification = next(item for item in notifications if item["id"] == notification_id)
    assert notification["status"] == "read"


@pytest.mark.anyio
async def test_unauthenticated_user_cannot_mark_all_notifications_as_read(
    client: AsyncClient,
) -> None:
    response = await client.patch(
        "/api/v1/notifications/read-all",
    )

    assert response.status_code == 401
