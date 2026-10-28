import pytest
from httpx import AsyncClient

from app.models.user import User


@pytest.mark.anyio
async def test_user_can_get_unread_notification_count(
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

    for index in range(2):
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

    response = await client.get(
        "/api/v1/notifications/unread-count",
        headers=headers,
    )

    assert response.status_code == 200

    body = response.json()
    assert body["success"] is True
    assert body["message"] == ("Unread notification count retrieved successfully")
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

    create_response = await client.post(
        "/api/v1/notifications",
        json={
            "type": "task_commented",
            "title": "Notification to mark read",
            "message": "This notification will be marked as read.",
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

    response = await client.get(
        "/api/v1/notifications/unread-count",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["data"]["unread_count"] == 0


@pytest.mark.anyio
async def test_unread_count_includes_only_current_users_notifications(
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
            "message": "This belongs to the second user.",
        },
        headers=second_headers,
    )
    assert create_response.status_code == 201

    response = await client.get(
        "/api/v1/notifications/unread-count",
        headers=first_headers,
    )

    assert response.status_code == 200
    assert response.json()["data"]["unread_count"] == 0


@pytest.mark.anyio
async def test_unauthenticated_user_cannot_get_unread_count(
    client: AsyncClient,
) -> None:
    response = await client.get(
        "/api/v1/notifications/unread-count",
    )

    assert response.status_code == 401
