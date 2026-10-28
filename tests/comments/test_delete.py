from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.models.task import Task


@pytest.mark.anyio
async def test_delete_own_comment(
    client: AsyncClient,
    test_task: Task,
    user_headers: dict[str, str],
) -> None:
    create_response = await client.post(
        f"/api/v1/tasks/{test_task.id}/comments",
        headers=user_headers,
        json={"content": "Comment to delete"},
    )

    assert create_response.status_code == 201
    comment_id = create_response.json()["data"]["id"]

    response = await client.delete(
        f"/api/v1/tasks/{test_task.id}/comments/{comment_id}",
        headers=user_headers,
    )

    assert response.status_code == 200
    assert response.json()["success"] is True

    # Verify that the deleted comment can no longer be retrieved.
    get_response = await client.patch(
        f"/api/v1/tasks/{test_task.id}/comments/{comment_id}",
        headers=user_headers,
        json={"content": "Try updating deleted comment"},
    )

    assert get_response.status_code == 404


@pytest.mark.anyio
async def test_admin_can_delete_another_users_comment(
    client: AsyncClient,
    test_task: Task,
    user_headers: dict[str, str],
    admin_headers: dict[str, str],
) -> None:
    create_response = await client.post(
        f"/api/v1/tasks/{test_task.id}/comments",
        headers=user_headers,
        json={"content": "Comment created by a regular user"},
    )

    assert create_response.status_code == 201
    comment_id = create_response.json()["data"]["id"]

    response = await client.delete(
        f"/api/v1/tasks/{test_task.id}/comments/{comment_id}",
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.json()["success"] is True


@pytest.mark.anyio
async def test_task_owner_cannot_delete_admins_comment(
    client: AsyncClient,
    test_task: Task,
    user_headers: dict[str, str],
    admin_headers: dict[str, str],
) -> None:
    create_response = await client.post(
        f"/api/v1/tasks/{test_task.id}/comments",
        headers=admin_headers,
        json={"content": "Comment created by admin"},
    )

    assert create_response.status_code == 201
    comment_id = create_response.json()["data"]["id"]

    response = await client.delete(
        f"/api/v1/tasks/{test_task.id}/comments/{comment_id}",
        headers=user_headers,
    )

    assert response.status_code == 404


@pytest.mark.anyio
async def test_delete_nonexistent_comment_returns_404(
    client: AsyncClient,
    test_task: Task,
    user_headers: dict[str, str],
) -> None:
    response = await client.delete(
        f"/api/v1/tasks/{test_task.id}/comments/{uuid4()}",
        headers=user_headers,
    )

    assert response.status_code == 404


@pytest.mark.anyio
async def test_unauthenticated_user_cannot_delete_comment(
    client: AsyncClient,
    test_task: Task,
    user_headers: dict[str, str],
) -> None:
    create_response = await client.post(
        f"/api/v1/tasks/{test_task.id}/comments",
        headers=user_headers,
        json={"content": "Comment to protect"},
    )

    assert create_response.status_code == 201
    comment_id = create_response.json()["data"]["id"]

    response = await client.delete(
        f"/api/v1/tasks/{test_task.id}/comments/{comment_id}",
    )

    assert response.status_code in (401, 403)
