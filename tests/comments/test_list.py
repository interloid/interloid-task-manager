import pytest
from httpx import AsyncClient

from app.models.task import Task


@pytest.mark.anyio
async def test_list_task_comments(
    client: AsyncClient,
    test_task: Task,
    user_headers: dict[str, str],
) -> None:
    for content in ("First comment", "Second comment"):
        create_response = await client.post(
            f"/api/v1/tasks/{test_task.id}/comments",
            headers=user_headers,
            json={"content": content},
        )
        assert create_response.status_code == 201

    response = await client.get(
        f"/api/v1/tasks/{test_task.id}/comments",
        headers=user_headers,
    )

    assert response.status_code == 200

    body = response.json()

    assert body["success"] is True
    assert body["message"] == "Comments retrieved successfully"
    assert len(body["data"]) == 2
    assert body["pagination"]["page"] == 1
    assert body["pagination"]["page_size"] == 20
    assert body["pagination"]["total"] == 2
    assert body["pagination"]["total_pages"] == 1


@pytest.mark.anyio
async def test_list_task_comments_pagination(
    client: AsyncClient,
    test_task: Task,
    user_headers: dict[str, str],
) -> None:
    for index in range(5):
        create_response = await client.post(
            f"/api/v1/tasks/{test_task.id}/comments",
            headers=user_headers,
            json={"content": f"Comment {index + 1}"},
        )
        assert create_response.status_code == 201

    first_response = await client.get(
        f"/api/v1/tasks/{test_task.id}/comments",
        headers=user_headers,
        params={"page": 1, "page_size": 2},
    )

    second_response = await client.get(
        f"/api/v1/tasks/{test_task.id}/comments",
        headers=user_headers,
        params={"page": 2, "page_size": 2},
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200

    first_body = first_response.json()
    second_body = second_response.json()

    assert len(first_body["data"]) == 2
    assert len(second_body["data"]) == 2

    assert first_body["pagination"]["total"] == 5
    assert first_body["pagination"]["total_pages"] == 3
    assert second_body["pagination"]["page"] == 2

    first_ids = {comment["id"] for comment in first_body["data"]}
    second_ids = {comment["id"] for comment in second_body["data"]}

    assert first_ids.isdisjoint(second_ids)


@pytest.mark.anyio
async def test_list_task_comments_empty(
    client: AsyncClient,
    test_task: Task,
    user_headers: dict[str, str],
) -> None:
    response = await client.get(
        f"/api/v1/tasks/{test_task.id}/comments",
        headers=user_headers,
    )

    assert response.status_code == 200

    body = response.json()

    assert body["data"] == []
    assert body["pagination"]["total"] == 0
    assert body["pagination"]["total_pages"] == 0


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("params", "expected_status"),
    [
        ({"page": 0}, 422),
        ({"page_size": 0}, 422),
        ({"page_size": 101}, 422),
    ],
)
async def test_list_comments_invalid_pagination_returns_422(
    client: AsyncClient,
    test_task: Task,
    user_headers: dict[str, str],
    params: dict[str, int],
    expected_status: int,
) -> None:
    response = await client.get(
        f"/api/v1/tasks/{test_task.id}/comments",
        headers=user_headers,
        params=params,
    )

    assert response.status_code == expected_status
