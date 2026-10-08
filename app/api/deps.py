from datetime import UTC, date, datetime
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Query
from fastapi.exceptions import RequestValidationError
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.db.dependencies import get_db
from app.enums import (
    RoleName,
    SortOrder,
    TaskPriority,
    TaskSortBy,
    TaskStatus,
    TokenType,
)
from app.exceptions.auth import ForbiddenException, UnauthorizedException
from app.models.user import User
from app.repositories.refresh_token import RefreshTokenRepository
from app.repositories.user import UserRepository
from app.schemas.task import TaskListQuery

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_db, scope="function"),
) -> User:
    if credentials is None:
        raise UnauthorizedException()

    token = credentials.credentials

    try:
        payload = decode_token(token)
    except InvalidTokenError as exc:
        raise UnauthorizedException() from exc

    if payload.get("type") != TokenType.ACCESS.value:
        raise UnauthorizedException()

    subject = payload.get("sub")

    if not isinstance(subject, str):
        raise UnauthorizedException()

    session_id = payload.get("sid")

    if not isinstance(session_id, str):
        raise UnauthorizedException()

    issued_at = payload.get("iat")

    if not isinstance(issued_at, int | float):
        raise UnauthorizedException()

    try:
        user_id = UUID(subject)
        family_id = UUID(session_id)
    except ValueError as exc:
        raise UnauthorizedException() from exc

    user_repository = UserRepository(session)

    user = await user_repository.get_by_id(user_id)

    if user is None:
        raise UnauthorizedException()

    if not user.is_active:
        raise UnauthorizedException()

    token_issued_at = datetime.fromtimestamp(
        issued_at,
        tz=UTC,
    )

    if (
        user.password_changed_at is not None
        and token_issued_at < user.password_changed_at
    ):
        raise UnauthorizedException()

    refresh_token_repository = RefreshTokenRepository(session)

    active_session = await refresh_token_repository.get_active_session_by_family_id(
        user_id=user.id, family_id=family_id
    )

    if active_session is None:
        raise UnauthorizedException()

    return user


async def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role != RoleName.ADMIN:
        raise ForbiddenException()

    return current_user


def get_task_list_query(
    owner_id: Annotated[UUID | None, Query()] = None,
    status: Annotated[TaskStatus | None, Query()] = None,
    priority: Annotated[TaskPriority | None, Query()] = None,
    due_from: Annotated[date | None, Query()] = None,
    due_to: Annotated[date | None, Query()] = None,
    search: Annotated[str | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    sort_by: Annotated[TaskSortBy, Query()] = TaskSortBy.CREATED_AT,
    order: Annotated[SortOrder, Query()] = SortOrder.DESC,
) -> TaskListQuery:
    try:
        return TaskListQuery(
            owner_id=owner_id,
            status=status,
            priority=priority,
            due_from=due_from,
            due_to=due_to,
            search=search,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            order=order,
        )
    except ValidationError as exc:
        raise RequestValidationError(
            exc.errors(),
        ) from exc


async def get_current_session_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> UUID:
    if credentials is None:
        raise UnauthorizedException()

    try:
        payload = decode_token(credentials.credentials)
    except InvalidTokenError as exc:
        raise UnauthorizedException() from exc

    if payload.get("type") != TokenType.ACCESS.value:
        raise UnauthorizedException()

    session_id = payload.get("sid")

    if not isinstance(session_id, str):
        raise UnauthorizedException()

    try:
        return UUID(session_id)
    except ValueError as exc:
        raise UnauthorizedException() from exc
