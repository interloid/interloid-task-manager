import pytest
from httpx import AsyncClient

from app.models.user import User


@pytest.mark.anyio
async def test_user_can_get_own_task_by_id(
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

    create_response = await client.post(
        "/api/v1/tasks",
        json={
            "title": "Get task by ID",
            "description": "Testing GET task by ID",
            "status": "Todo",
            "priority": "Medium",
            "due_date": "2026-09-10",
        },
        headers=headers,
    )

    assert create_response.status_code == 201

    created_task = create_response.json()["data"]
    id = created_task["id"]

    response = await client.get(
        f"/api/v1/tasks/{id}",
        headers=headers,
    )

    assert response.status_code == 200

    body = response.json()

    assert body["success"] is True
    assert body["message"] == "Task fetched successfully"

    task = body["data"]

    assert task["id"] == id
    assert task["owner_id"] == str(test_user.id)
    assert task["title"] == "Get task by ID"
    assert task["description"] == "Testing GET task by ID"
    assert task["status"] == "Todo"
    assert task["priority"] == "Medium"
    assert task["due_date"] == "2026-09-10"


@pytest.mark.anyio
async def test_get_task_by_id_returns_404_for_unknown_task(
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

    unknown_task_id = "01900000-0000-7000-8000-000000000001"

    response = await client.get(
        f"/api/v1/tasks/{unknown_task_id}",
        headers=headers,
    )

    assert response.status_code == 404

    body = response.json()

    assert body["success"] is False
    assert body["message"] == "Task not found"
    assert body["error"]["code"] == "TASK_NOT_FOUND"


@pytest.mark.anyio
async def test_user_cannot_get_another_users_task(
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

    user_headers = {
        "Authorization": f"Bearer {access_token}",
    }

    second_login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": second_user.email,
            "password": "Test1234",
        },
    )

    assert second_login_response.status_code == 200

    second_token = second_login_response.json()["data"]["access_token"]

    second_headers = {
        "Authorization": f"Bearer {second_token}",
    }

    create_response = await client.post(
        "/api/v1/tasks",
        json={
            "title": "Second user private task",
            "description": "Should not be visible to test_user",
            "status": "Todo",
            "priority": "Medium",
            "due_date": "2026-09-10",
        },
        headers=second_headers,
    )

    assert create_response.status_code == 201

    id = create_response.json()["data"]["id"]

    response = await client.get(
        f"/api/v1/tasks/{id}",
        headers=user_headers,
    )

    assert response.status_code == 404

    body = response.json()

    assert body["success"] is False
    assert body["message"] == "Task not found"
    assert body["error"]["code"] == "TASK_NOT_FOUND"


@pytest.mark.anyio
async def test_admin_can_get_another_users_task(
    client: AsyncClient,
    admin_user: User,
    test_user: User,
) -> None:
    user_login = await client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user.email,
            "password": "StrongPassword123!",
        },
    )

    assert user_login.status_code == 200

    user_token = user_login.json()["data"]["access_token"]

    user_headers = {
        "Authorization": f"Bearer {user_token}",
    }

    create_response = await client.post(
        "/api/v1/tasks",
        json={
            "title": "User task visible to admin",
            "description": "Admin should be able to fetch this",
            "status": "Todo",
            "priority": "Medium",
            "due_date": "2026-09-10",
        },
        headers=user_headers,
    )

    assert create_response.status_code == 201

    id = create_response.json()["data"]["id"]

    admin_login = await client.post(
        "/api/v1/auth/login",
        json={
            "email": admin_user.email,
            "password": "StrongPassword123!",
        },
    )

    assert admin_login.status_code == 200

    admin_token = admin_login.json()["data"]["access_token"]

    admin_headers = {
        "Authorization": f"Bearer {admin_token}",
    }

    response = await client.get(
        f"/api/v1/tasks/{id}",
        headers=admin_headers,
    )

    assert response.status_code == 200

    body = response.json()

    assert body["success"] is True
    assert body["message"] == "Task fetched successfully"

    task = body["data"]

    assert task["id"] == id
    assert task["owner_id"] == str(test_user.id)
    assert task["title"] == "User task visible to admin"
