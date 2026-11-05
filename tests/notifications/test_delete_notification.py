import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from tests.utils.notification import create_notification


@pytest.mark.anyio
async def test_user_can_delete_own_notification(
    client: AsyncClient,
    test_user: User,
    db_session: AsyncSession,
    user_headers: dict[str, str],
) -> None:
    notification = await create_notification(db_session, test_user)

    delete_response = await client.delete(
        f"/api/v1/notifications/{notification.id}",
        headers=user_headers,
    )

    assert delete_response.status_code == 200
    assert delete_response.json()["success"] is True
    assert delete_response.json()["message"] == "Notification deleted successfully"

    list_response = await client.get(
        "/api/v1/notifications",
        headers=user_headers,
    )

    assert list_response.status_code == 200

    notification_ids = {item["id"] for item in list_response.json()["data"]}
    assert str(notification.id) not in notification_ids


@pytest.mark.anyio
async def test_deleting_nonexistent_notification_returns_404(
    client: AsyncClient,
    test_user: User,
) -> None:
    from uuid import uuid4

    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user.email,
            "password": "StrongPassword123!",
        },
    )
    assert login_response.status_code == 200

    headers = {
        "Authorization": (f"Bearer {login_response.json()['data']['access_token']}"),
    }

    response = await client.delete(
        f"/api/v1/notifications/{uuid4()}",
        headers=headers,
    )

    assert response.status_code == 404


@pytest.mark.anyio
async def test_user_cannot_delete_another_users_notification(
    client: AsyncClient,
    test_user: User,
    second_user: User,
    db_session: AsyncSession,
    user_headers: dict[str, str],
    second_user_headers: dict[str, str],
) -> None:
    notification = await create_notification(db_session, second_user)

    response = await client.delete(
        f"/api/v1/notifications/{notification.id}",
        headers=user_headers,
    )

    assert response.status_code == 404

    owner_list_response = await client.get(
        "/api/v1/notifications",
        headers=second_user_headers,
    )

    assert owner_list_response.status_code == 200

    owner_notification_ids = {item["id"] for item in owner_list_response.json()["data"]}
    assert str(notification.id) in owner_notification_ids


@pytest.mark.anyio
async def test_unauthenticated_user_cannot_delete_notification(
    client: AsyncClient,
) -> None:
    response = await client.delete(
        "/api/v1/notifications/00000000-0000-0000-0000-000000000001",
    )

    assert response.status_code == 401


@pytest.mark.anyio
async def test_deleting_notification_twice_returns_404(
    client: AsyncClient,
    test_user: User,
    db_session: AsyncSession,
    user_headers: dict[str, str],
) -> None:
    notification = await create_notification(db_session, test_user)

    first_delete = await client.delete(
        f"/api/v1/notifications/{notification.id}",
        headers=user_headers,
    )
    assert first_delete.status_code == 200

    second_delete = await client.delete(
        f"/api/v1/notifications/{notification.id}",
        headers=user_headers,
    )
    assert second_delete.status_code == 404
