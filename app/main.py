from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from redis.asyncio import Redis
from starlette.middleware.sessions import SessionMiddleware

from app.api.v1.api import api_router
from app.core.config import settings
from app.core.logging import logger, setup_logging
from app.db.session import check_database_connection
from app.exceptions.base import AppException
from app.exceptions.handlers import (
    app_exception_handler,
    generic_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from app.middleware.cors import setup_cors
from app.middleware.process_time import ProcessTimeMiddleware
from app.middleware.request_id import RequestIDMiddleware
from app.middleware.request_logging import RequestLoggingMiddleware

setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await check_database_connection()
    logger.info("Database connected successfully")

    redis_client = Redis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
    )

    try:
        await redis_client.ping()
        app.state.redis = redis_client

        logger.info("Redis connected successfully")
        logger.info("Application started")

        yield

    finally:
        await redis_client.aclose()
        logger.info("Application stopped")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY.get_secret_value(),
    same_site="lax",
    https_only=not settings.DEBUG,
)

app.add_exception_handler(
    AppException,
    app_exception_handler,
)

app.add_exception_handler(
    HTTPException,
    http_exception_handler,
)


app.add_exception_handler(
    RequestValidationError,
    validation_exception_handler,
)

app.add_exception_handler(
    Exception,
    generic_exception_handler,
)

setup_cors(app)

app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(ProcessTimeMiddleware)

app.include_router(
    api_router,
    prefix="/api/v1",
)
