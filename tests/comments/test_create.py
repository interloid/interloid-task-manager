from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import NotificationType
from app.models import Notification, Task, User


@pytest.mark.anyio
async def test_create_task_comment(
    client: AsyncClient,
    test_task: Task,
    user_headers: dict[str, str],
) -> None:
    with patch(
        "app.services.task_comment_service.enqueue_email",
        new_callable=AsyncMock,
    ) as mock_enqueue_email:
        response = await client.post(
            f"/api/v1/tasks/{test_task.id}/comments",
            headers=user_headers,
            json={"content": "Completed the API validation."},
        )

    assert response.status_code == 201

    body = response.json()

    assert body["success"] is True
    assert body["message"] == "comment created successfully"
    assert body["data"]["task_id"] == str(test_task.id)
    assert body["data"]["user_id"] == str(test_task.owner_id)
    assert body["data"]["content"] == "Completed the API validation."
    assert body["data"]["id"] is not None
    assert body["data"]["created_at"] is not None
    assert body["data"]["updated_at"] is not None

    mock_enqueue_email.assert_not_awaited()


@pytest.mark.anyio
async def test_create_comment_with_blank_content_returns_422(
    client: AsyncClient,
    test_task: Task,
    user_headers: dict[str, str],
) -> None:
    response = await client.post(
        f"/api/v1/tasks/{test_task.id}/comments",
        headers=user_headers,
        json={"content": ""},
    )

    assert response.status_code == 422


@pytest.mark.anyio
async def test_create_comment_with_whitespace_returns_422(
    client: AsyncClient,
    test_task: Task,
    user_headers: dict[str, str],
) -> None:
    response = await client.post(
        f"/api/v1/tasks/{test_task.id}/comments",
        headers=user_headers,
        json={"content": "   \n  "},
    )

    assert response.status_code == 422


@pytest.mark.anyio
async def test_create_comment_exceeding_max_length_returns_422(
    client: AsyncClient,
    test_task: Task,
    user_headers: dict[str, str],
) -> None:
    response = await client.post(
        f"/api/v1/tasks/{test_task.id}/comments",
        headers=user_headers,
        json={"content": "a" * 5001},
    )

    assert response.status_code == 422


@pytest.mark.anyio
async def test_admin_comment_creates_notification_for_task_owner(
    client: AsyncClient,
    test_task: Task,
    test_user: User,
    admin_headers: dict[str, str],
    db_session,
) -> None:
    with patch(
        "app.services.task_comment_service.enqueue_email",
        new_callable=AsyncMock,
    ) as mock_enqueue_email:
        response = await client.post(
            f"/api/v1/tasks/{test_task.id}/comments",
            headers=admin_headers,
            json={"content": "Please review this task."},
        )

    assert response.status_code == 201

    mock_enqueue_email.assert_awaited_once()

    email_call = mock_enqueue_email.await_args
    assert email_call is not None

    email_kwargs = email_call.kwargs
    assert email_kwargs["to_email"] == test_user.email
    assert email_kwargs["subject"] == "New comment on your task"

    result = await db_session.execute(
        select(Notification).where(
            Notification.user_id == test_user.id,
            Notification.task_id == test_task.id,
            Notification.type == NotificationType.TASK_COMMENTED,
        )
    )
    notification = result.scalar_one_or_none()

    assert notification is not None
    assert notification.title == "New comment on your task"
    assert notification.message == "admin@example.com commented on your task."


@pytest.mark.anyio
async def test_owner_comment_does_not_create_notification(
    client: AsyncClient,
    test_task: Task,
    test_user: User,
    user_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    response = await client.post(
        f"/api/v1/tasks/{test_task.id}/comments",
        headers=user_headers,
        json={"content": "I have updated my task."},
    )

    assert response.status_code == 201

    result = await db_session.execute(
        select(Notification).where(
            Notification.user_id == test_user.id,
            Notification.task_id == test_task.id,
            Notification.type == NotificationType.TASK_COMMENTED,
        )
    )

    notification = result.scalar_one_or_none()

    assert notification is None


@pytest.mark.anyio
async def test_other_user_cannot_comment_on_another_users_task(
    client: AsyncClient,
    test_task: Task,
    second_user: User,
    second_user_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    query = (
        select(func.count())
        .select_from(Notification)
        .where(
            Notification.user_id == test_task.owner_id,
            Notification.task_id == test_task.id,
            Notification.type == NotificationType.TASK_COMMENTED,
        )
    )

    count_before = await db_session.scalar(query)

    response = await client.post(
        f"/api/v1/tasks/{test_task.id}/comments",
        headers=second_user_headers,
        json={"content": "I should not be able to comment here."},
    )

    assert response.status_code == 404

    count_after = await db_session.scalar(query)
    assert count_after == count_before
