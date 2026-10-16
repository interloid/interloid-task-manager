import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums.task import TaskPriority, TaskStatus
from app.models.task import Task
from app.models.task_attachment import TaskAttachment
from app.models.user import User


@pytest.mark.anyio
async def test_list_attachments_success(
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

    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user.email,
            "password": "StrongPassword123!",
        },
    )
    assert login_response.status_code == 200

    access_token = login_response.json()["data"]["access_token"]

    response = await client.get(
        f"/api/v1/tasks/{task.id}/attachments",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200

    body = response.json()
    assert body["success"] is True
    assert body["message"] == "Attachments retrieved successfully"
    assert len(body["data"]) == 1
    assert body["data"][0]["id"] == str(attachment.id)
    assert body["data"][0]["original_filename"] == "sample.pdf"
    assert body["data"][0]["content_type"] == "application/pdf"
    assert body["data"][0]["file_size"] == 100
