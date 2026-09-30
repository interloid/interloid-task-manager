import pytest
from httpx import AsyncClient

from app.models.user import User


@pytest.mark.anyio
async def test_get_tasks_returns_current_user_tasks(
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
        headers=headers,
        json={
            "title": "Pytest Task",
            "description": "Test GET tasks endpoint",
            "status": "Todo",
            "priority": "High",
            "due_date": "2026-09-10",
        },
    )

    assert create_response.status_code == 201

    response = await client.get(
        "/api/v1/tasks?page=1&page_size=20",
        headers=headers,
    )

    assert response.status_code == 200

    body = response.json()

    assert body["success"] is True
    assert body["message"] == "Tasks retrieved successfully"

    data = body["data"]
    pagination = body["pagination"]

    assert isinstance(data, list)

    assert pagination["total"] >= 1
    assert pagination["page_size"] == 20
    assert pagination["page"] == 1

    task = next(item for item in data if item["title"] == "Pytest Task")

    assert task["owner_id"] == str(test_user.id)
    assert task["title"] == "Pytest Task"
    assert task["status"] == "Todo"
    assert task["priority"] == "High"


@pytest.mark.anyio
async def test_get_tasks_with_filters_and_search(
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

    tasks = [
        {
            "title": "Deploy backend",
            "description": "Production deployment",
            "status": "Todo",
            "priority": "High",
            "due_date": "2026-09-10",
        },
        {
            "title": "Deploy frontend",
            "description": "Frontend deployment",
            "status": "Done",
            "priority": "High",
            "due_date": "2026-09-11",
        },
        {
            "title": "Write tests",
            "description": "Pytest",
            "status": "Todo",
            "priority": "High",
            "due_date": "2026-09-12",
        },
    ]

    for task in tasks:
        response = await client.post(
            "/api/v1/tasks",
            headers=headers,
            json=task,
        )

        assert response.status_code == 201

    response = await client.get(
        ("/api/v1/tasks?status=Todo&priority=High&search=deploy&page=1&page_size=2"),
        headers=headers,
    )

    assert response.status_code == 200

    body = response.json()

    assert body["success"] is True
    assert body["message"] == "Tasks retrieved successfully"

    data = body["data"]
    pagination = body["pagination"]

    assert pagination["total"] == 1
    assert pagination["page"] == 1
    assert pagination["page_size"] == 2
    assert pagination["total_pages"] == 1

    assert len(data) == 1

    task = data[0]

    assert task["title"] == "Deploy backend"
    assert task["status"] == "Todo"
    assert task["priority"] == "High"


@pytest.mark.anyio
async def test_get_tasks_rejects_limit_above_100(
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

    response = await client.get(
        "/api/v1/tasks?page_size=500",
        headers=headers,
    )

    assert response.status_code == 422

    body = response.json()

    assert body["success"] is False
    assert body["message"] == "Validation failed"
    assert body["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.anyio
async def test_get_tasks_rejects_inverted_due_date_range(
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

    response = await client.get(
        ("/api/v1/tasks?due_from=2026-09-01&due_to=2026-08-01"),
        headers=headers,
    )

    assert response.status_code == 422

    body = response.json()

    assert body["success"] is False
    assert body["message"] == "Validation failed"
    assert body["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.anyio
async def test_get_tasks_returns_only_current_user_tasks(
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
        "/api/v1/tasks",
        json={
            "title": "Current user task",
            "description": "Belongs to current user",
            "status": "Todo",
            "priority": "Medium",
            "due_date": "2026-09-01",
        },
        headers=headers,
    )

    print(response.status_code)
    print(response.json())

    assert response.status_code == 201

    response = await client.get(
        "/api/v1/tasks",
        headers=headers,
    )

    assert response.status_code == 200

    body = response.json()

    assert body["success"] is True
    assert body["message"] == "Tasks retrieved successfully"

    data = body["data"]

    assert isinstance(data, list)

    assert all(task["owner_id"] == str(test_user.id) for task in data)


@pytest.mark.anyio
async def test_admin_can_get_all_tasks(
    client: AsyncClient,
    admin_user: User,
    test_user: User,
) -> None:
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
            "title": "Normal user admin visibility task",
            "description": "Created by normal user",
            "status": "Todo",
            "priority": "Medium",
            "due_date": "2026-09-01",
        },
        headers=user_headers,
    )

    assert create_response.status_code == 201

    created_task = create_response.json()["data"]

    response = await client.get(
        "/api/v1/tasks",
        headers=admin_headers,
    )

    assert response.status_code == 200

    body = response.json()

    assert body["success"] is True
    assert body["message"] == "Tasks retrieved successfully"

    data = body["data"]

    assert any(
        task["id"] == created_task["id"] and task["owner_id"] == str(test_user.id)
        for task in data
    )


@pytest.mark.anyio
async def test_admin_can_filter_tasks_by_owner_id(
    client: AsyncClient,
    admin_user: User,
    test_user: User,
) -> None:
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
            "title": "Owner filter task",
            "description": "Task used for owner filter test",
            "status": "Todo",
            "priority": "Medium",
            "due_date": "2026-09-01",
        },
        headers=user_headers,
    )

    assert create_response.status_code == 201

    response = await client.get(
        f"/api/v1/tasks?owner_id={test_user.id}",
        headers=admin_headers,
    )

    assert response.status_code == 200

    body = response.json()

    assert body["success"] is True
    assert body["message"] == "Tasks retrieved successfully"

    data = body["data"]

    assert len(data) >= 1

    assert all(task["owner_id"] == str(test_user.id) for task in data)


@pytest.mark.anyio
async def test_get_tasks_filters_by_inclusive_due_date_range(
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

    first_response = await client.post(
        "/api/v1/tasks",
        json={
            "title": "Due range start task",
            "description": "Task exactly on due_from",
            "status": "Todo",
            "priority": "Medium",
            "due_date": "2026-09-01",
        },
        headers=headers,
    )

    assert first_response.status_code == 201

    second_response = await client.post(
        "/api/v1/tasks",
        json={
            "title": "Due range end task",
            "description": "Task exactly on due_to",
            "status": "Todo",
            "priority": "Medium",
            "due_date": "2026-09-10",
        },
        headers=headers,
    )

    assert second_response.status_code == 201

    response = await client.get(
        ("/api/v1/tasks?due_from=2026-09-01&due_to=2026-09-10"),
        headers=headers,
    )

    assert response.status_code == 200

    body = response.json()

    assert body["success"] is True
    assert body["message"] == "Tasks retrieved successfully"

    data = body["data"]

    titles = {task["title"] for task in data}

    assert "Due range start task" in titles
    assert "Due range end task" in titles


@pytest.mark.anyio
async def test_get_tasks_search_is_case_insensitive(
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
            "title": "Deploy Production API",
            "description": "Search test",
            "status": "Todo",
            "priority": "Medium",
            "due_date": "2026-09-10",
        },
        headers=headers,
    )

    assert create_response.status_code == 201

    response = await client.get(
        "/api/v1/tasks?search=deploy",
        headers=headers,
    )

    assert response.status_code == 200

    body = response.json()

    assert body["success"] is True
    assert body["message"] == "Tasks retrieved successfully"

    data = body["data"]

    assert any(task["title"] == "Deploy Production API" for task in data)


@pytest.mark.anyio
async def test_get_tasks_pagination_limit_and_offset(
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

    for number in range(1, 4):
        response = await client.post(
            "/api/v1/tasks",
            json={
                "title": f"Pagination Task {number}",
                "description": "Pagination test",
                "status": "Todo",
                "priority": "Medium",
                "due_date": "2026-09-10",
            },
            headers=headers,
        )

        assert response.status_code == 201

    response = await client.get(
        "/api/v1/tasks?search=Pagination%20Task&page=2&page_size=2",
        headers=headers,
    )

    assert response.status_code == 200

    body = response.json()

    assert body["success"] is True
    assert body["message"] == "Tasks retrieved successfully"

    data = body["data"]
    pagination = body["pagination"]

    assert pagination["total"] == 3
    assert pagination["page"] == 2
    assert pagination["page_size"] == 2
    assert pagination["total_pages"] == 2

    assert len(data) == 1


@pytest.mark.anyio
async def test_get_tasks_pagination_page_skips_records(
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

    for number in range(1, 4):
        response = await client.post(
            "/api/v1/tasks",
            json={
                "title": f"Offset Task {number}",
                "description": "Offset pagination test",
                "status": "Todo",
                "priority": "Medium",
                "due_date": "2026-09-10",
            },
            headers=headers,
        )

        assert response.status_code == 201

    response = await client.get(
        "/api/v1/tasks?search=Offset%20Task&page=2&page_size=2",
        headers=headers,
    )

    assert response.status_code == 200

    body = response.json()
    data = body["data"]
    pagination = body["pagination"]

    assert body["success"] is True
    assert body["message"] == "Tasks retrieved successfully"

    assert pagination["total"] == 3
    assert pagination["page"] == 2
    assert pagination["page_size"] == 2
    assert pagination["total_pages"] == 2

    assert len(data) == 1


@pytest.mark.anyio
async def test_normal_user_cannot_filter_tasks_by_another_owner(
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

    second_user_response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "secondtaskuser@example.com",
            "password": "Test1234",
            "first_name": "Second",
            "last_name": "User",
        },
    )

    assert second_user_response.status_code == 201

    second_user = second_user_response.json()["data"]
    second_user_id = second_user["id"]

    response = await client.get(
        f"/api/v1/tasks?owner_id={second_user_id}",
        headers=headers,
    )

    assert response.status_code == 200

    body = response.json()

    assert body["success"] is True
    assert body["message"] == "Tasks retrieved successfully"

    data = body["data"]

    data = body["data"]

    assert all(task["owner_id"] == str(test_user.id) for task in data)


@pytest.mark.anyio
async def test_tasks_sort_by_created_at_asc(
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

    for title in [
        "First Task",
        "Second Task",
        "Third Task",
    ]:
        response = await client.post(
            "/api/v1/tasks",
            headers=headers,
            json={
                "title": title,
                "priority": "Medium",
            },
        )

        assert response.status_code == 201

    response = await client.get(
        "/api/v1/tasks",
        params={
            "sort_by": "created_at",
            "order": "asc",
        },
        headers=headers,
    )

    assert response.status_code == 200

    body = response.json()

    assert body["success"] is True
    assert body["message"] == "Tasks retrieved successfully"

    data = body["data"]

    created_dates = [item["created_at"] for item in data]

    assert len(created_dates) == 3

    assert created_dates == sorted(
        created_dates,
    )


@pytest.mark.anyio
async def test_tasks_sort_by_created_at_desc(
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

    for title in [
        "First Task",
        "Second Task",
        "Third Task",
    ]:
        response = await client.post(
            "/api/v1/tasks",
            headers=headers,
            json={
                "title": title,
                "priority": "Medium",
            },
        )

        assert response.status_code == 201

    response = await client.get(
        "/api/v1/tasks",
        params={
            "sort_by": "created_at",
            "order": "desc",
        },
        headers=headers,
    )

    assert response.status_code == 200

    body = response.json()

    assert body["success"] is True
    assert body["message"] == "Tasks retrieved successfully"

    data = body["data"]

    created_dates = [item["created_at"] for item in data]

    assert len(created_dates) == 3

    assert created_dates == sorted(
        created_dates,
        reverse=True,
    )


@pytest.mark.anyio
async def test_tasks_sort_by_priority_asc(
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

    for title, priority in [
        ("High Task", "High"),
        ("Low Task", "Low"),
        ("Medium Task", "Medium"),
    ]:
        response = await client.post(
            "/api/v1/tasks",
            headers=headers,
            json={
                "title": title,
                "priority": priority,
            },
        )

        assert response.status_code == 201

    response = await client.get(
        "/api/v1/tasks",
        params={
            "sort_by": "priority",
            "order": "asc",
        },
        headers=headers,
    )

    assert response.status_code == 200

    body = response.json()

    assert body["success"] is True
    assert body["message"] == "Tasks retrieved successfully"

    data = body["data"]

    priorities = [item["priority"] for item in data]

    assert priorities == [
        "Low",
        "Medium",
        "High",
    ]


@pytest.mark.anyio
async def test_tasks_sort_by_priority_desc(
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

    for title, priority in [
        ("Low Task", "Low"),
        ("Medium Task", "Medium"),
        ("High Task", "High"),
    ]:
        response = await client.post(
            "/api/v1/tasks",
            headers=headers,
            json={
                "title": title,
                "priority": priority,
            },
        )

        assert response.status_code == 201

    response = await client.get(
        "/api/v1/tasks",
        params={
            "sort_by": "priority",
            "order": "desc",
        },
        headers=headers,
    )

    assert response.status_code == 200

    body = response.json()

    assert body["success"] is True
    assert body["message"] == "Tasks retrieved successfully"

    data = body["data"]

    priorities = [item["priority"] for item in data]

    assert priorities == [
        "High",
        "Medium",
        "Low",
    ]


@pytest.mark.anyio
async def test_tasks_sort_by_due_date_asc(
    client: AsyncClient,
    test_user: User,
) -> None:
    login_response = await client.post(
        "api/v1/auth/login",
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

    tasks = [
        {
            "title": "Later Task",
            "priority": "Medium",
            "due_date": "2026-09-15",
        },
        {
            "title": "No Due Date Task",
            "priority": "Medium",
            "due_date": None,
        },
        {
            "title": "Earlier Task",
            "priority": "Medium",
            "due_date": "2026-09-10",
        },
    ]

    for task in tasks:
        response = await client.post(
            "/api/v1/tasks",
            headers=headers,
            json=task,
        )

        assert response.status_code == 201

    response = await client.get(
        "/api/v1/tasks",
        params={
            "sort_by": "due_date",
            "order": "asc",
        },
        headers=headers,
    )

    assert response.status_code == 200

    body = response.json()

    assert body["success"] is True
    assert body["message"] == "Tasks retrieved successfully"

    data = body["data"]

    due_dates = [item["due_date"] for item in data]

    assert due_dates == [
        "2026-09-10",
        "2026-09-15",
        None,
    ]


@pytest.mark.anyio
async def test_tasks_sort_by_due_date_desc(
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

    tasks = [
        {
            "title": "Earlier Task",
            "priority": "Medium",
            "due_date": "2026-09-10",
        },
        {
            "title": "No Due Date Task",
            "priority": "Medium",
            "due_date": None,
        },
        {
            "title": "Later Task",
            "priority": "Medium",
            "due_date": "2026-09-15",
        },
    ]

    for task in tasks:
        response = await client.post(
            "/api/v1/tasks",
            headers=headers,
            json=task,
        )

        assert response.status_code == 201

    response = await client.get(
        "/api/v1/tasks",
        params={
            "sort_by": "due_date",
            "order": "desc",
        },
        headers=headers,
    )

    assert response.status_code == 200

    body = response.json()

    assert body["success"] is True
    assert body["message"] == "Tasks retrieved successfully"

    data = body["data"]

    due_dates = [item["due_date"] for item in data]

    assert due_dates == [
        "2026-09-15",
        "2026-09-10",
        None,
    ]


@pytest.mark.anyio
async def test_invalid_sort_by_returns_422(
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

    response = await client.get(
        "/api/v1/tasks",
        params={
            "sort_by": "invalid_field",
        },
        headers=headers,
    )

    assert response.status_code == 422


@pytest.mark.anyio
async def test_invalid_sort_order_returns_422(
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

    response = await client.get(
        "/api/v1/tasks",
        params={
            "order": "invalid_order",
        },
        headers=headers,
    )

    assert response.status_code == 422
