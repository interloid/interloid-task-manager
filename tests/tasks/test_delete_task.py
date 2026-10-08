import pytest
from httpx import AsyncClient

from app.models.user import User


@pytest.mark.anyio
async def test_user_can_delete_own_task(
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
            "title": "Task to delete",
            "description": "Delete test",
            "status": "Todo",
            "priority": "Medium",
            "due_date": "2026-09-10",
        },
        headers=headers,
    )

    assert create_response.status_code == 201

    id = create_response.json()["data"]["id"]

    response = await client.delete(
        f"/api/v1/tasks/{id}",
        headers=headers,
    )

    assert response.status_code == 200

    body = response.json()

    assert body["success"] is True
    assert body["message"] == "Task deleted successfully"


@pytest.mark.anyio
async def test_deleted_task_returns_404(
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
            "title": "Delete verification task",
            "description": "Verify task is really deleted",
            "status": "Todo",
            "priority": "Medium",
            "due_date": "2026-09-10",
        },
        headers=headers,
    )

    assert create_response.status_code == 201

    id = create_response.json()["data"]["id"]

    delete_response = await client.delete(
        f"/api/v1/tasks/{id}",
        headers=headers,
    )

    assert delete_response.status_code == 200

    get_response = await client.get(
        f"/api/v1/tasks/{id}",
        headers=headers,
    )

    assert get_response.status_code == 404

    body = get_response.json()

    assert body["success"] is False
    assert body["message"] == "Task not found"
    assert body["error"]["code"] == "TASK_NOT_FOUND"


@pytest.mark.anyio
async def test_user_cannot_delete_another_users_task(
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
            "title": "Second user delete task",
            "description": "Should not be deleted by another user",
            "status": "Todo",
            "priority": "Medium",
            "due_date": "2026-09-10",
        },
        headers=second_headers,
    )

    assert create_response.status_code == 201

    id = create_response.json()["data"]["id"]

    response = await client.delete(
        f"/api/v1/tasks/{id}",
        headers=user_headers,
    )

    assert response.status_code == 404

    body = response.json()

    assert body["success"] is False
    assert body["message"] == "Task not found"
    assert body["error"]["code"] == "TASK_NOT_FOUND"


@pytest.mark.anyio
async def test_admin_can_delete_another_users_task(
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
            "title": "Admin delete test",
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

    response = await client.delete(
        f"/api/v1/tasks/{id}",
        headers=admin_headers,
    )

    assert response.status_code == 200

    body = response.json()

    assert body["success"] is True
    assert body["message"] == "Task deleted successfully"


@pytest.mark.anyio
async def test_delete_task_returns_404_for_unknown_task(
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

    response = await client.delete(
        f"/api/v1/tasks/{unknown_task_id}",
        headers=headers,
    )

    assert response.status_code == 404

    body = response.json()

    assert body["success"] is False
    assert body["message"] == "Task not found"
    assert body["error"]["code"] == "TASK_NOT_FOUND"
