import pytest
from httpx import AsyncClient

from app.models.user import User


@pytest.mark.anyio
async def test_user_can_delete_all_read_notifications(
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

    notification_ids = []

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
        notification_ids.append(create_response.json()["data"]["id"])

    for notification_id in notification_ids[:2]:
        mark_read_response = await client.patch(
            f"/api/v1/notifications/{notification_id}/read",
            headers=headers,
        )
        assert mark_read_response.status_code == 200

    response = await client.delete(
        "/api/v1/notifications?status=read",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.json()["message"] == ("Read notifications deleted successfully")

    list_response = await client.get(
        "/api/v1/notifications",
        headers=headers,
    )
    assert list_response.status_code == 200

    remaining_ids = [
        notification["id"] for notification in list_response.json()["data"]
    ]

    assert notification_ids[2] in remaining_ids
    assert notification_ids[0] not in remaining_ids
    assert notification_ids[1] not in remaining_ids


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
            "title": "Unread notification",
            "message": "This notification must remain.",
        },
        headers=headers,
    )
    assert create_response.status_code == 201
    notification_id = create_response.json()["data"]["id"]

    response = await client.delete(
        "/api/v1/notifications?status=read",
        headers=headers,
    )
    assert response.status_code == 200

    list_response = await client.get(
        "/api/v1/notifications",
        headers=headers,
    )
    assert list_response.status_code == 200

    remaining_ids = [
        notification["id"] for notification in list_response.json()["data"]
    ]
    assert notification_id in remaining_ids


@pytest.mark.anyio
async def test_delete_read_notifications_only_affects_current_user(
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
            "title": "Second user's read notification",
            "message": "This belongs to the second user.",
        },
        headers=second_headers,
    )
    assert create_response.status_code == 201
    notification_id = create_response.json()["data"]["id"]

    mark_read_response = await client.patch(
        f"/api/v1/notifications/{notification_id}/read",
        headers=second_headers,
    )
    assert mark_read_response.status_code == 200

    response = await client.delete(
        "/api/v1/notifications?status=read",
        headers=first_headers,
    )
    assert response.status_code == 200

    second_list_response = await client.get(
        "/api/v1/notifications",
        headers=second_headers,
    )
    assert second_list_response.status_code == 200

    remaining_ids = [
        notification["id"] for notification in second_list_response.json()["data"]
    ]
    assert notification_id in remaining_ids


@pytest.mark.anyio
async def test_unauthenticated_user_cannot_delete_read_notifications(
    client: AsyncClient,
) -> None:
    response = await client.delete(
        "/api/v1/notifications?status=read",
    )

    assert response.status_code == 401
