from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_session_id, get_current_user
from app.api.responses import (
    NOT_FOUND_RESPONSE,
    UNAUTHORIZED_RESPONSE,
    VALIDATION_ERROR_RESPONSE,
)
from app.db.dependencies import get_db
from app.models import User
from app.schemas import APIResponse, MessageResponse, SessionListResponse
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["Session Management"])


@router.get(
    "/sessions",
    response_model=APIResponse[SessionListResponse],
    status_code=status.HTTP_200_OK,
    responses={
        **UNAUTHORIZED_RESPONSE,
    },
)
async def get_sessions(
    current_user: Annotated[
        User,
        Depends(get_current_user),
    ],
    current_session_id: Annotated[
        UUID,
        Depends(get_current_session_id),
    ],
    session: Annotated[
        AsyncSession,
        Depends(get_db, scope="function"),
    ],
) -> APIResponse[SessionListResponse]:
    service = AuthService(session)

    result = await service.get_sessions(
        user=current_user,
        current_session_id=current_session_id,
    )

    return APIResponse(
        message="Active sessions fetched successfully",
        data=result,
    )


@router.delete(
    "/sessions/{id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    responses={
        **UNAUTHORIZED_RESPONSE,
        **NOT_FOUND_RESPONSE,
        **VALIDATION_ERROR_RESPONSE,
    },
)
async def revoke_session(
    id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db, scope="function")],
) -> MessageResponse:
    service = AuthService(session)

    await service.revoke_session(
        user=current_user,
        family_id=id,
    )

    return MessageResponse(
        message="session revoked successfully",
    )


@router.post(
    "/logout-all",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    responses={
        **UNAUTHORIZED_RESPONSE,
    },
)
async def logout_all(
    current_user: Annotated[
        User,
        Depends(get_current_user),
    ],
    session: Annotated[
        AsyncSession,
        Depends(get_db, scope="function"),
    ],
) -> MessageResponse:
    service = AuthService(session)

    await service.logout_all(
        current_user,
    )

    return MessageResponse(
        message="logged out from all sessions successfully",
    )
