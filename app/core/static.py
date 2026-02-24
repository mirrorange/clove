from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger

from app.core.config import settings


def register_static_routes(app: FastAPI):
    """Register static file routes for the application."""

    if settings.static_folder.exists():
        app.mount(
            "/assets",
            StaticFiles(directory=str(settings.static_folder / "assets")),
            name="assets",
        )

        # Serve index.html for SPA routes
        @app.get("/{full_path:path}")
        async def serve_spa(full_path: str):
            """Serve index.html for all non-API routes (SPA support)."""
            index_path = settings.static_folder / "index.html"
            if index_path.exists():
                return FileResponse(str(index_path))
            raise HTTPException(status_code=404, detail="Frontend not built")
    else:
        logger.warning(
            "Static files directory not found. Run 'pnpm build' in the front directory to build the frontend."
        )
