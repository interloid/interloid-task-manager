from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.models.user import User


@pytest.mark.anyio
async def test_user_can_create_notification(
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

    headers = {
        "Authorization": f"Bearer {access_token}",
    }

    response = await client.post(
        "/api/v1/notifications",
        json={
            "type": "task_commented",
            "title": "New comment",
            "message": "A new comment was added to your task.",
        },
        headers=headers,
    )

    assert response.status_code == 201

    body = response.json()

    assert body["success"] is True
    assert body["message"] == "Notification created successfully"

    notification = body["data"]

    assert notification["user_id"] == str(test_user.id)
    assert notification["task_id"] is None
    assert notification["type"] == "task_commented"
    assert notification["title"] == "New comment"
    assert notification["message"] == "A new comment was added to your task."
    assert notification["status"] == "unread"


@pytest.mark.anyio
async def test_user_can_create_notification_for_own_task(
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
    headers = {
        "Authorization": f"Bearer {access_token}",
    }

    task_response = await client.post(
        "/api/v1/tasks",
        json={
            "title": "Notification test task",
            "description": "Testing notification with a task",
            "status": "Todo",
            "priority": "Medium",
            "due_date": "2026-10-30",
        },
        headers=headers,
    )

    assert task_response.status_code == 201

    task_id = task_response.json()["data"]["id"]

    response = await client.post(
        "/api/v1/notifications",
        json={
            "task_id": task_id,
            "type": "task_commented",
            "title": "New task comment",
            "message": "A comment was added to your task.",
        },
        headers=headers,
    )

    assert response.status_code == 201

    body = response.json()

    assert body["success"] is True

    notification = body["data"]

    assert notification["user_id"] == str(test_user.id)
    assert notification["task_id"] == task_id
    assert notification["type"] == "task_commented"
    assert notification["title"] == "New task comment"
    assert notification["status"] == "unread"


@pytest.mark.anyio
async def test_user_cannot_create_notification_for_nonexistent_task(
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
    headers = {
        "Authorization": f"Bearer {access_token}",
    }

    response = await client.post(
        "/api/v1/notifications",
        json={
            "task_id": str(uuid4()),
            "type": "task_commented",
            "title": "New task comment",
            "message": "A comment was added to your task.",
        },
        headers=headers,
    )

    assert response.status_code == 404


@pytest.mark.anyio
async def test_unauthenticated_user_cannot_create_notification(
    client: AsyncClient,
) -> None:
    response = await client.post(
        "/api/v1/notifications",
        json={
            "type": "task_commented",
            "title": "New comment",
            "message": "A new comment was added to your task.",
        },
    )

    assert response.status_code == 401


@pytest.mark.anyio
async def test_user_cannot_create_notification_with_empty_title(
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
    headers = {
        "Authorization": f"Bearer {access_token}",
    }

    response = await client.post(
        "/api/v1/notifications",
        json={
            "type": "task_commented",
            "title": "",
            "message": "A new comment was added to your task.",
        },
        headers=headers,
    )

    assert response.status_code == 422


@pytest.mark.anyio
async def test_user_cannot_create_notification_with_empty_message(
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
    headers = {
        "Authorization": f"Bearer {access_token}",
    }

    response = await client.post(
        "/api/v1/notifications",
        json={
            "type": "task_commented",
            "title": "New comment",
            "message": "",
        },
        headers=headers,
    )

    assert response.status_code == 422


@pytest.mark.anyio
async def test_user_cannot_create_notification_with_invalid_type(
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
    headers = {
        "Authorization": f"Bearer {access_token}",
    }

    response = await client.post(
        "/api/v1/notifications",
        json={
            "type": "invalid_type",
            "title": "New notification",
            "message": "Testing invalid notification type.",
        },
        headers=headers,
    )

    assert response.status_code == 422


@pytest.mark.anyio
async def test_user_cannot_create_notification_with_long_title(
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
    headers = {
        "Authorization": f"Bearer {access_token}",
    }

    response = await client.post(
        "/api/v1/notifications",
        json={
            "type": "task_commented",
            "title": "A" * 201,
            "message": "Testing a title that exceeds the maximum length.",
        },
        headers=headers,
    )

    assert response.status_code == 422


@pytest.mark.anyio
async def test_user_cannot_create_notification_without_type(
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
    headers = {
        "Authorization": f"Bearer {access_token}",
    }

    response = await client.post(
        "/api/v1/notifications",
        json={
            "title": "New notification",
            "message": "Testing a missing notification type.",
        },
        headers=headers,
    )

    assert response.status_code == 422


@pytest.mark.anyio
async def test_user_cannot_create_notification_without_title(
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
    headers = {
        "Authorization": f"Bearer {access_token}",
    }

    response = await client.post(
        "/api/v1/notifications",
        json={
            "type": "task_commented",
            "message": "Testing a missing title.",
        },
        headers=headers,
    )

    assert response.status_code == 422


@pytest.mark.anyio
async def test_user_cannot_create_notification_without_message(
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
    headers = {
        "Authorization": f"Bearer {access_token}",
    }

    response = await client.post(
        "/api/v1/notifications",
        json={
            "type": "task_commented",
            "title": "New notification",
        },
        headers=headers,
    )

    assert response.status_code == 422


@pytest.mark.anyio
async def test_user_can_create_notification_with_whitespace_title(
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
    headers = {
        "Authorization": f"Bearer {access_token}",
    }

    response = await client.post(
        "/api/v1/notifications",
        json={
            "type": "task_commented",
            "title": "   ",
            "message": "Testing a whitespace-only title.",
        },
        headers=headers,
    )

    assert response.status_code == 201
    assert response.json()["data"]["title"] == "   "


@pytest.mark.anyio
async def test_user_can_create_notification_with_whitespace_message(
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
    headers = {
        "Authorization": f"Bearer {access_token}",
    }

    response = await client.post(
        "/api/v1/notifications",
        json={
            "type": "task_commented",
            "title": "New notification",
            "message": "   ",
        },
        headers=headers,
    )

    assert response.status_code == 201
    assert response.json()["data"]["message"] == "   "
