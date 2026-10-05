from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError

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
    logger.info("Application started")

    yield

    logger.info("Application stopped")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
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

