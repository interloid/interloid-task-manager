import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums.task import TaskPriority, TaskStatus
from app.models.task import Task
from app.models.user import User


@pytest.mark.anyio
async def test_user_cannot_create_comment_on_another_users_task(
    client: AsyncClient,
    db_session: AsyncSession,
    second_user: User,
    user_headers: dict[str, str],
) -> None:
    task = Task(
        owner_id=second_user.id,
        title="Another user's task",
        status=TaskStatus.TODO,
        priority=TaskPriority.MEDIUM,
    )

    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)

    response = await client.post(
        f"/api/v1/tasks/{task.id}/comments",
        headers=user_headers,
        json={"content": "Unauthorized comment"},
    )

    assert response.status_code == 404


@pytest.mark.anyio
async def test_user_cannot_list_another_users_task_comments(
    client: AsyncClient,
    db_session: AsyncSession,
    second_user: User,
    user_headers: dict[str, str],
) -> None:
    task = Task(
        owner_id=second_user.id,
        title="Another user's task",
        status=TaskStatus.TODO,
        priority=TaskPriority.MEDIUM,
    )

    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)

    response = await client.get(
        f"/api/v1/tasks/{task.id}/comments",
        headers=user_headers,
    )

    assert response.status_code == 404


@pytest.mark.anyio
async def test_admin_can_list_another_users_task_comments(
    client: AsyncClient,
    test_task: Task,
    user_headers: dict[str, str],
    admin_headers: dict[str, str],
) -> None:
    create_response = await client.post(
        f"/api/v1/tasks/{test_task.id}/comments",
        headers=user_headers,
        json={"content": "Comment on task"},
    )

    assert create_response.status_code == 201

    response = await client.get(
        f"/api/v1/tasks/{test_task.id}/comments",
        headers=admin_headers,
    )

    assert response.status_code == 200

    body = response.json()
    assert body["success"] is True
    assert any(comment["content"] == "Comment on task" for comment in body["data"])


@pytest.mark.anyio
async def test_user_cannot_update_another_users_task_comment(
    client: AsyncClient,
    db_session: AsyncSession,
    second_user: User,
    user_headers: dict[str, str],
) -> None:
    task = Task(
        owner_id=second_user.id,
        title="Another user's task",
        status=TaskStatus.TODO,
        priority=TaskPriority.MEDIUM,
    )

    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)

    response = await client.patch(
        f"/api/v1/tasks/{task.id}/comments/00000000-0000-0000-0000-000000000001",
        headers=user_headers,
        json={"content": "Unauthorized update"},
    )

    assert response.status_code == 404


@pytest.mark.anyio
async def test_user_cannot_delete_another_users_task_comment(
    client: AsyncClient,
    db_session: AsyncSession,
    second_user: User,
    user_headers: dict[str, str],
) -> None:
    task = Task(
        owner_id=second_user.id,
        title="Another user's task",
        status=TaskStatus.TODO,
        priority=TaskPriority.MEDIUM,
    )

    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)

    response = await client.delete(
        f"/api/v1/tasks/{task.id}/comments/00000000-0000-0000-0000-000000000001",
        headers=user_headers,
    )

    assert response.status_code == 404


@pytest.mark.anyio
async def test_unauthenticated_user_cannot_list_comments(
    client: AsyncClient,
    test_task: Task,
) -> None:
    response = await client.get(
        f"/api/v1/tasks/{test_task.id}/comments",
    )

    assert response.status_code in (401, 403)
