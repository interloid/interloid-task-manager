from unittest.mock import patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums.task import TaskPriority, TaskStatus
from app.models.task import Task
from app.models.task_attachment import TaskAttachment
from app.models.user import User


@pytest.mark.anyio
async def test_delete_attachment_success(
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
    await db_session.flush()

    attachment = TaskAttachment(
        task_id=task.id,
        uploaded_by_id=test_user.id,
        original_filename="sample.pdf",
        storage_key=f"tasks/{task.id}/test-object",
        content_type="application/pdf",
        file_size=100,
    )
    db_session.add(attachment)
    await db_session.commit()
    await db_session.refresh(attachment)

    task_id = task.id
    attachment_id = attachment.id

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

        response = await client.delete(
            f"/api/v1/tasks/{task_id}/attachments/{attachment_id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.json()["message"] == "Attachment deleted successfully"
    mock_storage.assert_awaited_once()

    db_session.expire_all()

    deleted_attachment = await db_session.get(
        TaskAttachment,
        attachment_id,
    )

    assert deleted_attachment is None
