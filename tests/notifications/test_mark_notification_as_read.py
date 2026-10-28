from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.models.user import User


@pytest.mark.anyio
async def test_user_can_mark_own_notification_as_read(
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
            "title": "New comment",
            "message": "Someone commented on your task.",
        },
        headers=headers,
    )

    assert create_response.status_code == 201

    notification_id = create_response.json()["data"]["id"]

    response = await client.patch(
        f"/api/v1/notifications/{notification_id}/read",
        headers=headers,
    )

    assert response.status_code == 200

    body = response.json()

    assert body["success"] is True
    assert body["message"] == "Notification marked as read successfully"
    assert body["data"]["id"] == notification_id
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

    create_response = await client.post(
        "/api/v1/notifications",
        json={
            "type": "task_commented",
            "title": "Private notification",
            "message": "This belongs to the first user.",
        },
        headers=first_headers,
    )
    assert create_response.status_code == 201

    notification_id = create_response.json()["data"]["id"]

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

    response = await client.patch(
        f"/api/v1/notifications/{notification_id}/read",
        headers=second_headers,
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
            "title": "Already read test",
            "message": "Testing repeated read updates.",
        },
        headers=headers,
    )
    assert create_response.status_code == 201

    notification_id = create_response.json()["data"]["id"]

    first_response = await client.patch(
        f"/api/v1/notifications/{notification_id}/read",
        headers=headers,
    )
    assert first_response.status_code == 200
    assert first_response.json()["data"]["status"] == "read"

    second_response = await client.patch(
        f"/api/v1/notifications/{notification_id}/read",
        headers=headers,
    )
    assert second_response.status_code == 200
    assert second_response.json()["data"]["status"] == "read"
