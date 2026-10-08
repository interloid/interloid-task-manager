import os
from collections.abc import AsyncGenerator

import pytest
from limits.aio.storage import MemoryStorage
from limits.aio.strategies import MovingWindowRateLimiter
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from uuid6 import uuid7

from app.core.config import settings
from app.core.rate_limit import login_rate_limiter
from app.core.security import hash_password
from app.db.dependencies import get_db
from app.mail.dependencies import get_mailer
from app.mail.fake import FakeMailer
from app.enums import RoleName
from app.main import app
from app.models.user import User


def validate_test_database() -> None:
    if os.getenv("ENV_FILE") != ".env.test":
        raise RuntimeError("Tests must be run with ENV_FILE=.env.test")


validate_test_database()


test_engine = create_async_engine(
    settings.database_url,
    echo=False,
)

TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    autoflush=False,
    expire_on_commit=False,
)


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


app.dependency_overrides[get_db] = override_get_db


async def truncate_tables() -> None:
    async with test_engine.begin() as connection:
        await connection.execute(
            text(
                """
                TRUNCATE TABLE
                    refresh_tokens,
                    tasks,
                    users
                CASCADE
                """
            )
        )


@pytest.fixture(autouse=True)
async def clean_database() -> AsyncGenerator[None, None]:
    await truncate_tables()

    yield

    await truncate_tables()


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as async_client:  
        yield async_client


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        yield session


@pytest.fixture
async def test_user(
    db_session: AsyncSession,
) -> User:
    user = User(
        id=uuid7(),
        email="testuser@example.com",
        password_hash=hash_password("StrongPassword123!"),
        first_name="Test",
        last_name="User",
        role=RoleName.USER,
        is_active=True,
        is_verified=True,
    )

    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    return user


@pytest.fixture
async def inactive_user(
    db_session: AsyncSession,
) -> User:
    user = User(
        id=uuid7(),
        email="inactive@example.com",
        password_hash=hash_password("StrongPassword123!"),
        first_name="Inactive",
        last_name="User",
        role=RoleName.USER,
        is_active=False,
        is_verified=True,
    )

    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    return user


@pytest.fixture
async def admin_user(
    db_session: AsyncSession,
) -> User:
    user = User(
        id=uuid7(),
        email="admin@example.com",
        password_hash=hash_password("StrongPassword123!"),
        first_name="Admin",
        last_name="User",
        role=RoleName.ADMIN,
        is_active=True,
        is_verified=True,
    )

    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    return user


@pytest.fixture
async def second_admin(
    db_session: AsyncSession,
) -> User:
    user = User(
        id=uuid7(),
        email="admin2@example.com",
        password_hash=hash_password("StrongPassword123!"),
        first_name="Second",
        last_name="Admin",
        role=RoleName.ADMIN,
        is_active=True,
        is_verified=True,
    )

    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    return user


@pytest.fixture
async def second_user(
    db_session: AsyncSession,
) -> User:
    user = User(
        id=uuid7(),
        email="seconduser@example.com",
        password_hash=hash_password("Test1234"),
        first_name="Second",
        last_name="User",
        role=RoleName.USER,
        is_active=True,
        is_verified=True,
    )

    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    return user


@pytest.fixture(autouse=True)
async def reset_login_rate_limiter() -> AsyncGenerator[
    None,
    None,
]:
    login_rate_limiter.storage = MemoryStorage()

    login_rate_limiter.limiter = MovingWindowRateLimiter(
        login_rate_limiter.storage,
    )

    await login_rate_limiter.reset()

    yield

    await login_rate_limiter.reset()

@pytest.fixture(autouse=True)
def override_mailer():
    app.dependency_overrides[get_mailer] = lambda: FakeMailer()

    yield

    app.dependency_overrides.pop(get_mailer, None)
