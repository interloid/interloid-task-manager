from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.models.task import Task


@pytest.mark.anyio
async def test_update_own_comment(
    client: AsyncClient,
    test_task: Task,
    user_headers: dict[str, str],
) -> None:
    create_response = await client.post(
        f"/api/v1/tasks/{test_task.id}/comments",
        headers=user_headers,
        json={"content": "Original comment"},
    )

    assert create_response.status_code == 201
    comment_id = create_response.json()["data"]["id"]

    response = await client.patch(
        f"/api/v1/tasks/{test_task.id}/comments/{comment_id}",
        headers=user_headers,
        json={"content": "Updated comment"},
    )

    assert response.status_code == 200

    body = response.json()
    assert body["success"] is True
    assert body["data"]["id"] == comment_id
    assert body["data"]["content"] == "Updated comment"


@pytest.mark.anyio
async def test_admin_can_update_another_users_comment(
    client: AsyncClient,
    test_task: Task,
    user_headers: dict[str, str],
    admin_headers: dict[str, str],
) -> None:
    create_response = await client.post(
        f"/api/v1/tasks/{test_task.id}/comments",
        headers=user_headers,
        json={"content": "Comment written by a regular user"},
    )

    assert create_response.status_code == 201
    comment_id = create_response.json()["data"]["id"]

    response = await client.patch(
        f"/api/v1/tasks/{test_task.id}/comments/{comment_id}",
        headers=admin_headers,
        json={"content": "Comment edited by admin"},
    )

    assert response.status_code == 200
    assert response.json()["data"]["content"] == "Comment edited by admin"


@pytest.mark.anyio
async def test_task_owner_cannot_update_admins_comment(
    client: AsyncClient,
    test_task: Task,
    user_headers: dict[str, str],
    admin_headers: dict[str, str],
) -> None:
    create_response = await client.post(
        f"/api/v1/tasks/{test_task.id}/comments",
        headers=admin_headers,
        json={"content": "Comment written by admin"},
    )

    assert create_response.status_code == 201
    comment_id = create_response.json()["data"]["id"]

    response = await client.patch(
        f"/api/v1/tasks/{test_task.id}/comments/{comment_id}",
        headers=user_headers,
        json={"content": "Attempted unauthorized edit"},
    )

    assert response.status_code == 404


@pytest.mark.anyio
async def test_update_nonexistent_comment_returns_404(
    client: AsyncClient,
    test_task: Task,
    user_headers: dict[str, str],
) -> None:
    response = await client.patch(
        f"/api/v1/tasks/{test_task.id}/comments/{uuid4()}",
        headers=user_headers,
        json={"content": "Updated comment"},
    )

    assert response.status_code == 404
