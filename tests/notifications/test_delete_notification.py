import pytest
from httpx import AsyncClient

from app.models.user import User


@pytest.mark.anyio
async def test_user_can_delete_own_notification(
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
            "title": "Notification to delete",
            "message": "This notification will be deleted.",
        },
        headers=headers,
    )
    assert create_response.status_code == 201
    notification_id = create_response.json()["data"]["id"]

    delete_response = await client.delete(
        f"/api/v1/notifications/{notification_id}",
        headers=headers,
    )

    assert delete_response.status_code == 200
    assert delete_response.json()["success"] is True
    assert delete_response.json()["message"] == ("Notification deleted successfully")

    list_response = await client.get(
        "/api/v1/notifications",
        headers=headers,
    )
    assert list_response.status_code == 200

    notification_ids = [
        notification["id"] for notification in list_response.json()["data"]
    ]
    assert notification_id not in notification_ids


@pytest.mark.anyio
async def test_deleting_nonexistent_notification_returns_404(
    client: AsyncClient,
    test_user: User,
) -> None:
    from uuid import uuid4

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
        f"/api/v1/notifications/{uuid4()}",
        headers=headers,
    )

    assert response.status_code == 404


@pytest.mark.anyio
async def test_user_cannot_delete_another_users_notification(
    client: AsyncClient,
    test_user: User,
    second_user: User,
) -> None:
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
            "title": "Private notification",
            "message": "This belongs to the second user.",
        },
        headers=second_headers,
    )
    assert create_response.status_code == 201
    notification_id = create_response.json()["data"]["id"]

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

    response = await client.delete(
        f"/api/v1/notifications/{notification_id}",
        headers=first_headers,
    )

    assert response.status_code == 404

    owner_list_response = await client.get(
        "/api/v1/notifications",
        headers=second_headers,
    )
    assert owner_list_response.status_code == 200

    owner_notification_ids = [
        notification["id"] for notification in owner_list_response.json()["data"]
    ]
    assert notification_id in owner_notification_ids


@pytest.mark.anyio
async def test_unauthenticated_user_cannot_delete_notification(
    client: AsyncClient,
) -> None:
    response = await client.delete(
        "/api/v1/notifications/00000000-0000-0000-0000-000000000001",
    )

    assert response.status_code == 401


@pytest.mark.anyio
async def test_deleting_notification_twice_returns_404(
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
            "title": "Delete twice test",
            "message": "This notification will be deleted once.",
        },
        headers=headers,
    )
    assert create_response.status_code == 201
    notification_id = create_response.json()["data"]["id"]

    first_delete = await client.delete(
        f"/api/v1/notifications/{notification_id}",
        headers=headers,
    )
    assert first_delete.status_code == 200

    second_delete = await client.delete(
        f"/api/v1/notifications/{notification_id}",
        headers=headers,
    )
    assert second_delete.status_code == 404
