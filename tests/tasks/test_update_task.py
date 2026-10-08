import pytest
from httpx import AsyncClient

from app.models.user import User


@pytest.mark.anyio
async def test_user_can_update_own_task(
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
            "title": "Original task title",
            "description": "Original description",
            "status": "Todo",
            "priority": "Medium",
            "due_date": "2026-09-10",
        },
        headers=headers,
    )

    assert create_response.status_code == 201

    id = create_response.json()["data"]["id"]

    response = await client.patch(
        f"/api/v1/tasks/{id}",
        json={
            "title": "Updated task title",
            "status": "Done",
            "priority": "High",
        },
        headers=headers,
    )

    assert response.status_code == 200

    body = response.json()

    assert body["success"] is True
    assert body["message"] == "Task updated successfully"

    task = body["data"]

    assert task["id"] == id
    assert task["owner_id"] == str(test_user.id)

    assert task["title"] == "Updated task title"
    assert task["status"] == "Done"
    assert task["priority"] == "High"

    assert task["description"] == "Original description"
    assert task["due_date"] == "2026-09-10"


@pytest.mark.anyio
async def test_update_task_returns_404_for_unknown_task(
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

    response = await client.patch(
        f"/api/v1/tasks/{unknown_task_id}",
        json={
            "status": "Done",
        },
        headers=headers,
    )

    assert response.status_code == 404

    body = response.json()

    assert body["success"] is False
    assert body["message"] == "Task not found"
    assert body["error"]["code"] == "TASK_NOT_FOUND"


@pytest.mark.anyio
async def test_user_cannot_update_another_users_task(
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

    user_token = login_response.json()["data"]["access_token"]

    user_headers = {
        "Authorization": f"Bearer {user_token}",
    }

    second_login = await client.post(
        "/api/v1/auth/login",
        json={
            "email": second_user.email,
            "password": "Test1234",
        },
    )

    assert second_login.status_code == 200

    second_token = second_login.json()["data"]["access_token"]

    second_headers = {
        "Authorization": f"Bearer {second_token}",
    }

    create_response = await client.post(
        "/api/v1/tasks",
        json={
            "title": "Second user task",
            "description": "Private task",
            "status": "Todo",
            "priority": "Medium",
            "due_date": "2026-09-10",
        },
        headers=second_headers,
    )

    assert create_response.status_code == 201

    id = create_response.json()["data"]["id"]

    response = await client.patch(
        f"/api/v1/tasks/{id}",
        json={
            "status": "Done",
        },
        headers=user_headers,
    )

    assert response.status_code == 404

    body = response.json()

    assert body["success"] is False
    assert body["message"] == "Task not found"
    assert body["error"]["code"] == "TASK_NOT_FOUND"


@pytest.mark.anyio
async def test_admin_can_update_another_users_task(
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
            "title": "Task before admin update",
            "description": "Owned by normal user",
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

    response = await client.patch(
        f"/api/v1/tasks/{id}",
        json={
            "status": "Done",
            "priority": "High",
        },
        headers=admin_headers,
    )

    assert response.status_code == 200

    body = response.json()

    assert body["success"] is True
    assert body["message"] == "Task updated successfully"

    task = body["data"]

    assert task["id"] == id
    assert task["owner_id"] == str(test_user.id)
    assert task["status"] == "Done"
    assert task["priority"] == "High"


@pytest.mark.anyio
async def test_update_task_rejects_invalid_status(
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
            "title": "Invalid status test",
            "description": "Testing invalid PATCH status",
            "status": "Todo",
            "priority": "Medium",
            "due_date": "2026-09-10",
        },
        headers=headers,
    )

    assert create_response.status_code == 201

    id = create_response.json()["data"]["id"]

    response = await client.patch(
        f"/api/v1/tasks/{id}",
        json={
            "status": "InvalidStatus",
        },
        headers=headers,
    )

    assert response.status_code == 422

    body = response.json()

    assert body["success"] is False
    assert body["message"] == "Validation failed"
    assert body["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.anyio
async def test_update_task_rejects_invalid_priority(
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
            "title": "Invalid priority test",
            "description": "Testing invalid PATCH priority",
            "status": "Todo",
            "priority": "Medium",
            "due_date": "2026-09-10",
        },
        headers=headers,
    )

    assert create_response.status_code == 201

    id = create_response.json()["data"]["id"]

    response = await client.patch(
        f"/api/v1/tasks/{id}",
        json={
            "priority": "Critical",
        },
        headers=headers,
    )

    assert response.status_code == 422

    body = response.json()

    assert body["success"] is False
    assert body["message"] == "Validation failed"
    assert body["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.anyio
async def test_update_task_with_null_title_returns_422(
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
            "title": "Null title test",
            "description": "Testing null title",
            "status": "Todo",
            "priority": "Medium",
            "due_date": "2026-09-10",
        },
        headers=headers,
    )

    assert create_response.status_code == 201

    task_id = create_response.json()["data"]["id"]

    response = await client.patch(
        f"/api/v1/tasks/{task_id}",
        json={
            "title": None,
        },
        headers=headers,
    )

    assert response.status_code == 422

    body = response.json()

    assert body["success"] is False
    assert body["message"] == "Validation failed"
    assert body["error"]["code"] == "VALIDATION_ERROR"

    assert "title cannot be null" in str(body["error"]["details"])


@pytest.mark.anyio
async def test_update_task_with_null_status_returns_422(
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
            "title": "Null status test",
            "description": "Testing null status",
            "status": "Todo",
            "priority": "Medium",
            "due_date": "2026-09-10",
        },
        headers=headers,
    )

    assert create_response.status_code == 201

    task_id = create_response.json()["data"]["id"]

    response = await client.patch(
        f"/api/v1/tasks/{task_id}",
        json={
            "status": None,
        },
        headers=headers,
    )

    assert response.status_code == 422

    body = response.json()

    assert body["success"] is False
    assert body["message"] == "Validation failed"
    assert body["error"]["code"] == "VALIDATION_ERROR"

    assert "status cannot be null" in str(body["error"]["details"])


@pytest.mark.anyio
async def test_update_task_with_null_priority_returns_422(
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
            "title": "Null priority test",
            "description": "Testing null priority",
            "status": "Todo",
            "priority": "Medium",
            "due_date": "2026-09-10",
        },
        headers=headers,
    )

    assert create_response.status_code == 201

    task_id = create_response.json()["data"]["id"]

    response = await client.patch(
        f"/api/v1/tasks/{task_id}",
        json={
            "priority": None,
        },
        headers=headers,
    )

    assert response.status_code == 422

    body = response.json()

    assert body["success"] is False
    assert body["message"] == "Validation failed"
    assert body["error"]["code"] == "VALIDATION_ERROR"

    assert "priority cannot be null" in str(body["error"]["details"])
