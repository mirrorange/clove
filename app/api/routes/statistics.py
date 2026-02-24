from typing import Literal
from fastapi import APIRouter
from pydantic import BaseModel

from app.dependencies.auth import AdminAuthDep
from app.services.account import account_manager


class AccountStats(BaseModel):
    total_accounts: int
    valid_accounts: int
    rate_limited_accounts: int
    invalid_accounts: int
    active_sessions: int


class StatisticsResponse(BaseModel):
    status: Literal["healthy", "degraded"]
    accounts: AccountStats


router = APIRouter()


@router.get("", response_model=StatisticsResponse)
async def get_statistics(_: AdminAuthDep):
    """Get system statistics. Requires admin authentication."""
    stats = await account_manager.get_status()
    return {
        "status": "healthy" if stats["valid_accounts"] > 0 else "degraded",
        "accounts": stats,
    }
