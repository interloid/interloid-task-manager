import ssl

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

connect_args: dict[str, object] = {}

if settings.DB_SSL:
    ssl_context = ssl.create_default_context()
    connect_args["ssl"] = ssl_context


engine = create_async_engine(
    settings.database_url,
    echo=settings.DEBUG,
    connect_args=connect_args,
    pool_pre_ping=True,
)


AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autoflush=False,
    expire_on_commit=False,
)


async def check_database_connection() -> None:
    async with engine.begin() as connection:
        await connection.execute(
            text("SELECT 1"),
        )
