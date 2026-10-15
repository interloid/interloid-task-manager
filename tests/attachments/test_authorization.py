from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.enums import RoleName
from app.enums.task import TaskPriority, TaskStatus
from app.models.task import Task
from app.models.task_attachment import TaskAttachment
from app.models.user import User


@pytest.mark.anyio
async def test_user_cannot_access_another_users_attachment(
    client: AsyncClient,
    test_user: User,
    db_session: AsyncSession,
) -> None:
    another_user = User(
        id=uuid4(),
        email="anotheruser@example.com",
        password_hash=hash_password("StrongPassword123!"),
        first_name="Another",
        last_name="User",
        role=RoleName.USER,
        is_active=True,
        is_verified=True,
    )
    db_session.add(another_user)
    await db_session.flush()

    task = Task(
        owner_id=another_user.id,
        title="Another user's task",
        status=TaskStatus.TODO,
        priority=TaskPriority.MEDIUM,
    )
    db_session.add(task)
    await db_session.flush()

    attachment = TaskAttachment(
        task_id=task.id,
        uploaded_by_id=another_user.id,
        original_filename="private.pdf",
        storage_key=f"tasks/{task.id}/private.pdf",
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
    headers = {"Authorization": f"Bearer {access_token}"}

    list_response = await client.get(
        f"/api/v1/tasks/{task_id}/attachments",
        headers=headers,
    )
    assert list_response.status_code == 404

    details_response = await client.get(
        f"/api/v1/tasks/{task_id}/attachments/{attachment_id}",
        headers=headers,
    )
    assert details_response.status_code == 404

    download_response = await client.get(
        f"/api/v1/tasks/{task_id}/attachments/{attachment_id}/download",
        headers=headers,
    )
    assert download_response.status_code == 404

    delete_response = await client.delete(
        f"/api/v1/tasks/{task_id}/attachments/{attachment_id}",
        headers=headers,
    )
    assert delete_response.status_code == 404
