import sys
from pathlib import Path
from loguru import logger

from app.core.config import settings


def configure_logger():
    """Initialize the logger with console and optional file output."""
    logger.remove()

    logger.add(
        sys.stdout,
        level=settings.log_level.upper(),
        colorize=True,
    )

    if settings.log_to_file:
        log_file = Path(settings.log_file_path)
        log_file.parent.mkdir(parents=True, exist_ok=True)

        logger.add(
            settings.log_file_path,
            level=settings.log_level.upper(),
            rotation=settings.log_file_rotation,
            retention=settings.log_file_retention,
            compression=settings.log_file_compression,
            enqueue=True,
            encoding="utf-8",
        )
