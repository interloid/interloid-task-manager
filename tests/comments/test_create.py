import pytest
from httpx import AsyncClient

from app.models.task import Task


@pytest.mark.anyio
async def test_create_task_comment(
    client: AsyncClient,
    test_task: Task,
    user_headers: dict[str, str],
) -> None:
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
