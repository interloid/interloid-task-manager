from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.enums import NotificationType
from app.models import Notification, Task, User
from tests.conftest import TestSessionLocal


@pytest.mark.anyio
async def test_create_task_success(
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

    access_token = login_response.json()["data"]["access_token"]

    response = await client.post(
        "/api/v1/tasks",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
        json={
            "title": "Learn FastAPI",
            "description": "Complete Task CRUD",
            "status": "Todo",
            "priority": "High",
            "due_date": "2026-09-05",
        },
    )

    assert response.status_code == 201

    body = response.json()

    assert body["success"] is True
    assert body["message"] == "Task created successfully"

    assert body["data"]["title"] == "Learn FastAPI"
    assert body["data"]["description"] == "Complete Task CRUD"
    assert body["data"]["status"] == "Todo"
    assert body["data"]["priority"] == "High"
    assert body["data"]["due_date"] == "2026-09-05"

    assert body["data"]["owner_id"] == str(test_user.id)


@pytest.mark.anyio
async def test_admin_assigns_task_and_queues_email(
    client: AsyncClient,
    admin_headers: dict[str, str],
    test_user: User,
    db_session,
) -> None:
    with patch(
        "app.services.task.enqueue_email",
        new_callable=AsyncMock,
    ) as mock_enqueue_email:
        response = await client.post(
            "/api/v1/tasks",
            headers=admin_headers,
            json={
                "title": "Review API validation",
                "description": "Review the task validation logic",
                "owner_id": str(test_user.id),
            },
        )

    assert response.status_code == 201

    body = response.json()
    assert body["data"]["owner_id"] == str(test_user.id)

    mock_enqueue_email.assert_awaited_once()

    email_call = mock_enqueue_email.await_args
    assert email_call is not None

    email_kwargs = email_call.kwargs
    assert email_kwargs["to_email"] == test_user.email
    assert email_kwargs["subject"] == "A new task has been assigned to you"

    result = await db_session.execute(
        select(Notification).where(
            Notification.user_id == test_user.id,
            Notification.task_id == body["data"]["id"],
            Notification.type == NotificationType.TASK_ASSIGNED,
        )
    )

    notification = result.scalar_one_or_none()

    assert notification is not None
    assert notification.title == "New task assigned to you"


@pytest.mark.anyio
async def test_admin_assigns_task_to_nonexistent_user(
    client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    with patch(
        "app.services.task.enqueue_email",
        new_callable=AsyncMock,
    ) as mock_enqueue_email:
        response = await client.post(
            "/api/v1/tasks",
            headers=admin_headers,
            json={
                "title": "Review API validation",
                "owner_id": "00000000-0000-0000-0000-000000000001",
            },
        )

    assert response.status_code == 404
    mock_enqueue_email.assert_not_awaited()


@pytest.mark.anyio
async def test_normal_user_creates_task_without_assignment_email(
    client: AsyncClient,
    user_headers: dict[str, str],
    test_user: User,
) -> None:
    with patch(
        "app.services.task.enqueue_email",
        new_callable=AsyncMock,
    ) as mock_enqueue_email:
        response = await client.post(
            "/api/v1/tasks",
            headers=user_headers,
            json={
                "title": "Complete API testing",
                "description": "Write task creation tests",
            },
        )

    assert response.status_code == 201

    body = response.json()
    assert body["data"]["owner_id"] == str(test_user.id)

    mock_enqueue_email.assert_not_awaited()


@pytest.mark.anyio
async def test_normal_user_cannot_assign_task_to_another_user(
    client: AsyncClient,
    user_headers: dict[str, str],
    test_user: User,
    second_user: User,
) -> None:
    with patch(
        "app.services.task.enqueue_email",
        new_callable=AsyncMock,
    ) as mock_enqueue_email:
        response = await client.post(
            "/api/v1/tasks",
            headers=user_headers,
            json={
                "title": "My task",
                "owner_id": str(second_user.id),
            },
        )

    assert response.status_code == 201

    body = response.json()
    assert body["data"]["owner_id"] == str(test_user.id)
    assert body["data"]["owner_id"] != str(second_user.id)

    mock_enqueue_email.assert_not_awaited()


@pytest.mark.anyio
async def test_admin_assignment_fails_when_email_queue_is_unavailable(
    client: AsyncClient,
    admin_headers: dict[str, str],
    test_user: User,
) -> None:
    with patch(
        "app.services.task.enqueue_email",
        new_callable=AsyncMock,
        side_effect=RuntimeError("Redis is unavailable"),
    ) as mock_enqueue_email:
        with pytest.raises(
            RuntimeError,
            match="Redis is unavailable",
        ):
            await client.post(
                "/api/v1/tasks",
                headers=admin_headers,
                json={
                    "title": "Task when Redis is down",
                    "owner_id": str(test_user.id),
                },
            )

    mock_enqueue_email.assert_awaited_once()


@pytest.mark.anyio
async def test_admin_assignment_rolls_back_when_email_queue_fails(
    client: AsyncClient,
    admin_headers: dict[str, str],
    test_user: User,
) -> None:
    task_title = "Task when Redis is down"

    with patch(
        "app.services.task.enqueue_email",
        new_callable=AsyncMock,
        side_effect=RuntimeError("Redis is unavailable"),
    ) as mock_enqueue_email:
        with pytest.raises(
            RuntimeError,
            match="Redis is unavailable",
        ):
            await client.post(
                "/api/v1/tasks",
                headers=admin_headers,
                json={
                    "title": task_title,
                    "owner_id": str(test_user.id),
                },
            )

    mock_enqueue_email.assert_awaited_once()

    async with TestSessionLocal() as verification_session:
        task_result = await verification_session.execute(
            select(Task).where(Task.title == task_title)
        )
        assert task_result.scalar_one_or_none() is None

        notification_result = await verification_session.execute(
            select(Notification).where(
                Notification.user_id == test_user.id,
                Notification.title == "New task assigned to you",
            )
        )
        assert notification_result.scalars().all() == []
