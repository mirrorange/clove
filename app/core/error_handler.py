from typing import Dict, Any
from fastapi import Request
from fastapi.responses import JSONResponse
from loguru import logger

from app.services.i18n import i18n_service
from app.core.exceptions import AppError


class ErrorHandler:
    """
    Centralized error handler for the application. Handles AppException.
    """

    @staticmethod
    def get_language_from_request(request: Request) -> str:
        """Extract language preference from request headers."""
        accept_language = request.headers.get("accept-language")
        return i18n_service.parse_accept_language(accept_language)

    @staticmethod
    def format_error_response(
        error_code: int, message: str, context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Format error response in standardized format.

        Args:
            error_code: 6-digit error code
            message: Localized error message
            context: Additional context information

        Returns:
            Formatted error response
        """
        response = {"detail": {"code": error_code, "message": message}}

        # Add context if provided and not empty
        if context:
            response["detail"]["context"] = context

        return response

    @staticmethod
    async def handle_app_exception(request: Request, exc: AppError) -> JSONResponse:
        """
        Handle AppException instances.

        Args:
            request: The FastAPI request object
            exc: The AppException instance

        Returns:
            JSONResponse with localized error message
        """
        language = ErrorHandler.get_language_from_request(request)

        # Get localized message
        message = i18n_service.get_message(
            message_key=exc.message_key, language=language, context=exc.context
        )

        # Format response
        response_data = ErrorHandler.format_error_response(
            error_code=exc.error_code,
            message=message,
            context=exc.context if exc.context else None,
        )

        # Log the error
        logger.warning(
            f"AppException: {exc.__class__.__name__} - "
            f"Code: {exc.error_code}, Message: {message}, "
            f"Context: {exc.context}"
        )

        return JSONResponse(status_code=exc.status_code, content=response_data)


# Exception handler functions for FastAPI
async def app_exception_handler(request: Request, exc: AppError) -> JSONResponse:
    """FastAPI exception handler for AppException."""
    return await ErrorHandler.handle_app_exception(request, exc)
