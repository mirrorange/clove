from fastapi import APIRouter
from app.api.routes import claude, accounts, settings, statistics

api_router = APIRouter()

api_router.include_router(claude.router, prefix="/v1", tags=["Claude API"])
api_router.include_router(
    accounts.router, prefix="/api/admin/accounts", tags=["Account Management"]
)
api_router.include_router(
    settings.router, prefix="/api/admin/settings", tags=["Settings Management"]
)
api_router.include_router(
    statistics.router, prefix="/api/admin/statistics", tags=["Statistics"]
)
