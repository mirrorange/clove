from loguru import logger
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.main import api_router
from app.core.config import settings
from app.core.error_handler import app_exception_handler
from app.core.exceptions import AppError
from app.core.static import register_static_routes
from app.utils.logger import configure_logger
from app.services.account import account_manager
from app.services.session import session_manager
from app.services.tool_call import tool_call_manager
from app.services.cache import cache_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting Clove...")

    configure_logger()

    # Load accounts
    account_manager.load_accounts()

    for cookie in settings.cookies:
        await account_manager.add_account(cookie_value=cookie)

    # Start tasks
    await account_manager.start_task()
    await session_manager.start_cleanup_task()
    await tool_call_manager.start_cleanup_task()
    await cache_service.start_cleanup_task()

    yield

    logger.info("Shutting down Clove...")

    # Save accounts
    account_manager.save_accounts()

    # Stop tasks
    await account_manager.stop_task()
    await session_manager.cleanup_all()
    await tool_call_manager.cleanup_all()
    await cache_service.cleanup_all()


app = FastAPI(
    title="Clove",
    description="A Claude.ai reverse proxy",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(api_router)

# Static files
register_static_routes(app)

# Exception handlers
app.add_exception_handler(AppError, app_exception_handler)


# Health check
@app.get("/health")
async def health():
    """Health check endpoint."""
    stats = await account_manager.get_status()
    return {"status": "healthy" if stats["valid_accounts"] > 0 else "degraded"}


def main():
    """Main entry point for the application."""
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )


if __name__ == "__main__":
    main()
