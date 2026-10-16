import io
from unittest.mock import patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums.task import TaskPriority, TaskStatus
from app.models.task import Task
from app.models.user import User


@pytest.mark.anyio
async def test_upload_attachment_success(
    client: AsyncClient,
    test_user: User,
    db_session: AsyncSession,
) -> None:
    task = Task(
        owner_id=test_user.id,
        title="Test attachment task",
        status=TaskStatus.TODO,
        priority=TaskPriority.MEDIUM,
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)

    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user.email,
            "password": "StrongPassword123!",
        },
    )
    assert login_response.status_code == 200

    access_token = login_response.json()["data"]["access_token"]

    with patch(
        "app.services.task_attachment_service.run_in_threadpool",
    ) as mock_storage:
        mock_storage.return_value = None

        response = await client.post(
            f"/api/v1/tasks/{task.id}/attachments",
            headers={"Authorization": f"Bearer {access_token}"},
            files={
                "file": (
                    "sample.pdf",
                    io.BytesIO(b"%PDF-1.4 sample content"),
                    "application/pdf",
                ),
            },
        )
    print(response.json())
    assert response.status_code == 201

    body = response.json()
    assert body["success"] is True
    assert body["message"] == "Attachment uploaded successfully"
    assert body["data"]["original_filename"] == "sample.pdf"
    assert body["data"]["content_type"] == "application/pdf"
    assert body["data"]["file_size"] > 0

    mock_storage.assert_awaited_once()
