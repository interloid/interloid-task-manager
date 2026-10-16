import logging
from typing import Literal

from authlib.integrations.base_client.errors import OAuthError
from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.oauth import oauth
from app.db.dependencies import get_db
from app.exceptions.auth import BadRequestException, UnauthorizedException
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
        raise BadRequestException()

    redirect_uri = settings.GOOGLE_REDIRECT_URI

    return await client.authorize_redirect(request, redirect_uri)


@router.get(
    "/callback",
    name="oauth_callback",
    response_class=RedirectResponse,
    responses={
        status.HTTP_303_SEE_OTHER: {
            "description": "Redirect to the frontend after successful OAuth login."
        },
    },
)
async def oauth_callback(
    provider: OAuthProvider,
    request: Request,
    session: AsyncSession = Depends(get_db, scope="function"),
):
    client = oauth.create_client(provider)

    if client is None:
        raise BadRequestException()

    try:
        token = await client.authorize_access_token(request)

    except OAuthError as exc:
        raise UnauthorizedException() from exc

    claims = token.get("userinfo")

    if not claims:
        raise UnauthorizedException()

    service = OAuthService(session)

    result = await service.login(
        provider=provider,
        claims=claims,
        user_agent=request.headers.get("user-agent"),
    )

    response = RedirectResponse(
        url=settings.FRONTEND_URL,
        status_code=status.HTTP_303_SEE_OTHER,
    )

    response.set_cookie(
        key="access_token",
        value=result.access_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )

    response.set_cookie(
        key="refresh_token",
        value=result.refresh_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/",
    )

    return response
