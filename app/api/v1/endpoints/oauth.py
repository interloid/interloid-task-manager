import logging
from typing import Literal

from authlib.integrations.base_client.errors import OAuthError
from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.oauth import oauth
from app.db.dependencies import get_db
from app.exceptions.auth import UnauthorizedException
from app.services.oauth import OAuthService

router = APIRouter(
    prefix="/auth/{provider}",
    tags=["OAuth Authentication"],
)

OAuthProvider = Literal["google"]

logger = logging.getLogger(__name__)


@router.get(
    "/login",
    status_code=status.HTTP_307_TEMPORARY_REDIRECT,
)
async def oauth_login(
    provider: OAuthProvider,
    request: Request,
) -> RedirectResponse:
    client = oauth.create_client(provider)

    if client is None:
        raise UnauthorizedException()

    redirect_uri = request.url_for(
        "oauth_callback",
        provider=provider,
    )

    return await client.authorize_redirect(
        request,
        str(redirect_uri),
    )


@router.get(
    "/callback",
    name="oauth_callback",
)
async def oauth_callback(
    provider: OAuthProvider,
    request: Request,
    session: AsyncSession = Depends(get_db, scope="function"),
):
    client = oauth.create_client(provider)

    if client is None:
        raise UnauthorizedException()

    try:
        token = await client.authorize_access_token(request)
    except OAuthError as exc:
        raise UnauthorizedException() from exc

    claims = token.get("userinfo")

    if not claims:
        raise UnauthorizedException()

    service = OAuthService(session)

    return await service.login(
        provider=provider,
        claims=claims,
        user_agent=request.headers.get("user-agent"),
    )
