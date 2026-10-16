import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.oauth import oauth
from app.models.oauth_account import OAuthAccount
from app.models.refresh_token import RefreshToken
from app.models.user import User


class FakeGoogleOAuthClient:
    async def authorize_access_token(self, request):
        return {
            "userinfo": {
                "sub": "google-test-user-123",
                "email": "oauth-first-time@example.com",
                "email_verified": True,
                "given_name": "Test",
                "family_name": "User",
            }
        }


class FakeGoogleOAuthClientWithClaims:
    def __init__(self, claims: dict) -> None:
        self.claims = claims

    async def authorize_access_token(self, request):
        return {"userinfo": self.claims}


@pytest.mark.asyncio
async def test_existing_google_user_login(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    oauth_account = OAuthAccount(
        user_id=test_user.id,
        provider="google",
        provider_user_id="google-test-user-123",
        email=test_user.email,
    )
    db_session.add(oauth_account)
    await db_session.commit()

    monkeypatch.setattr(
        oauth,
        "create_client",
        lambda provider: FakeGoogleOAuthClient(),
    )

    response = await client.get(
        "/api/v1/auth/google/callback",
    )

    assert response.status_code == 303
    assert response.headers["location"] == settings.FRONTEND_URL

    set_cookie_headers = response.headers.get_list("set-cookie")

    assert any(
        cookie.startswith("access_token=") and "HttpOnly" in cookie
        for cookie in set_cookie_headers
    )

    assert any(
        cookie.startswith("refresh_token=") and "HttpOnly" in cookie
        for cookie in set_cookie_headers
    )

    user_count = await db_session.scalar(select(func.count()).select_from(User))
    oauth_account_count = await db_session.scalar(
        select(func.count()).select_from(OAuthAccount)
    )
    refresh_token_count = await db_session.scalar(
        select(func.count()).select_from(RefreshToken)
    )

    assert user_count == 1
    assert oauth_account_count == 1
    assert refresh_token_count == 1


async def test_first_time_google_user_login(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        oauth,
        "create_client",
        lambda provider: FakeGoogleOAuthClient(),
    )

    response = await client.get(
        "/api/v1/auth/google/callback",
    )

    assert response.status_code == 303
    assert response.headers["location"] == settings.FRONTEND_URL
    set_cookie_headers = response.headers.get_list("set-cookie")
    assert any(
        cookie.startswith("access_token=") and "HttpOnly" in cookie
        for cookie in set_cookie_headers
    )
    assert any(
        cookie.startswith("refresh_token=") and "HttpOnly" in cookie
        for cookie in set_cookie_headers
    )
    user = await db_session.scalar(
        select(User).where(
            User.email == "oauth-first-time@example.com",
        )
    )
    assert user is not None
    assert user.is_verified is True
    assert user.is_active is True

    oauth_account = await db_session.scalar(
        select(OAuthAccount).where(
            OAuthAccount.provider == "google",
            OAuthAccount.provider_user_id == "google-test-user-123",
        )
    )
    assert oauth_account is not None
    assert oauth_account.user_id == user.id

    user_count = await db_session.scalar(select(func.count()).select_from(User))
    oauth_account_count = await db_session.scalar(
        select(func.count()).select_from(OAuthAccount)
    )
    refresh_token_count = await db_session.scalar(
        select(func.count()).select_from(RefreshToken)
    )

    assert user_count == 1
    assert oauth_account_count == 1
    assert refresh_token_count == 1


async def test_google_login_existing_email_returns_conflict(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        oauth,
        "create_client",
        lambda provider: FakeGoogleOAuthClientWithClaims(
            {
                "sub": "unlinked-google-user-456",
                "email": "testuser@example.com",
                "email_verified": True,
                "given_name": "Test",
                "family_name": "User",
            }
        ),
    )

    response = await client.get(
        "/api/v1/auth/google/callback",
    )

    assert response.status_code == 409

    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "OAUTH_ACCOUNT_CONFLICT"

    user_count = await db_session.scalar(select(func.count()).select_from(User))
    oauth_account_count = await db_session.scalar(
        select(func.count()).select_from(OAuthAccount)
    )
    refresh_token_count = await db_session.scalar(
        select(func.count()).select_from(RefreshToken)
    )

    assert user_count == 1
    assert oauth_account_count == 0
    assert refresh_token_count == 0


async def test_inactive_google_user_login_returns_401(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    test_user.is_active = False

    oauth_account = OAuthAccount(
        user_id=test_user.id,
        provider="google",
        provider_user_id="google-test-user-123",
        email=test_user.email,
    )
    db_session.add(oauth_account)
    await db_session.commit()

    monkeypatch.setattr(
        oauth,
        "create_client",
        lambda provider: FakeGoogleOAuthClient(),
    )

    response = await client.get(
        "/api/v1/auth/google/callback",
    )

    assert response.status_code == 401

    body = response.json()
    assert body["success"] is False

    user_count = await db_session.scalar(select(func.count()).select_from(User))
    oauth_account_count = await db_session.scalar(
        select(func.count()).select_from(OAuthAccount)
    )
    refresh_token_count = await db_session.scalar(
        select(func.count()).select_from(RefreshToken)
    )

    assert user_count == 1
    assert oauth_account_count == 1
    assert refresh_token_count == 0


async def test_google_login_unverified_email_returns_401(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        oauth,
        "create_client",
        lambda provider: FakeGoogleOAuthClientWithClaims(
            {
                "sub": "google-unverified-user-123",
                "email": "unverified@example.com",
                "email_verified": False,
                "given_name": "Unverified",
                "family_name": "User",
            }
        ),
    )

    response = await client.get(
        "/api/v1/auth/google/callback",
    )

    assert response.status_code == 401

    user_count = await db_session.scalar(select(func.count()).select_from(User))
    oauth_account_count = await db_session.scalar(
        select(func.count()).select_from(OAuthAccount)
    )
    refresh_token_count = await db_session.scalar(
        select(func.count()).select_from(RefreshToken)
    )

    assert user_count == 0
    assert oauth_account_count == 0
    assert refresh_token_count == 0


async def test_google_login_missing_email_returns_401(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        oauth,
        "create_client",
        lambda provider: FakeGoogleOAuthClientWithClaims(
            {
                "sub": "google-missing-email-123",
                "email_verified": True,
                "given_name": "Test",
                "family_name": "User",
            }
        ),
    )

    response = await client.get(
        "/api/v1/auth/google/callback",
    )

    assert response.status_code == 401

    user_count = await db_session.scalar(select(func.count()).select_from(User))
    oauth_account_count = await db_session.scalar(
        select(func.count()).select_from(OAuthAccount)
    )
    refresh_token_count = await db_session.scalar(
        select(func.count()).select_from(RefreshToken)
    )

    assert user_count == 0
    assert oauth_account_count == 0
    assert refresh_token_count == 0
