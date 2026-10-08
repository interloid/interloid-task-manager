from fastapi import APIRouter

from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.email_auth import router as email_router
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.password_recovery import router as password_router
from app.api.v1.endpoints.session import router as sessions_router
from app.api.v1.endpoints.tasks import router as tasks_router
from app.api.v1.endpoints.user_profile import router as profile_router
from app.api.v1.endpoints.users import router as users_router

api_router = APIRouter()

api_router.include_router(health_router)

api_router.include_router(auth_router)

api_router.include_router(email_router)

api_router.include_router(password_router)

api_router.include_router(sessions_router)

api_router.include_router(profile_router)

api_router.include_router(users_router)

api_router.include_router(tasks_router)
