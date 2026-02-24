from datetime import datetime
from typing import Optional, Any, Dict


class AppError(Exception):
    """
    Base class for application-specific exceptions.
    """

    def __init__(
        self,
        error_code: int,
        message_key: str,
        status_code: int,
        context: Optional[Dict[str, Any]] = None,
        retryable: bool = False,
    ):
        self.error_code = error_code
        self.message_key = message_key
        self.status_code = status_code
        self.context = context if context is not None else {}
        self.retryable = retryable
        super().__init__(
            f"Error Code: {error_code}, Message Key: {message_key}, Context: {self.context}"
        )

    def __str__(self):
        return f"{self.__class__.__name__}(error_code={self.error_code}, message_key='{self.message_key}', status_code={self.status_code}, context={self.context})"


class InternalServerError(AppError):
    def __init__(self, context: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code=500000,
            message_key="global.internalServerError",
            status_code=500,
            context=context,
        )


class NoAPIKeyProvidedError(AppError):
    def __init__(self, context: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code=401010,
            message_key="global.noAPIKeyProvided",
            status_code=401,
            context=context,
        )


class InvalidAPIKeyError(AppError):
    def __init__(self, context: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code=401011,
            message_key="global.invalidAPIKey",
            status_code=401,
            context=context,
        )


class NoAccountsAvailableError(AppError):
    def __init__(self, context: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code=503100,
            message_key="accountManager.noAccountsAvailable",
            status_code=503,
            context=context,
            retryable=True,
        )


class ClaudeRateLimitedError(AppError):
    resets_at: datetime

    def __init__(self, resets_at: datetime, context: Optional[Dict[str, Any]] = None):
        self.resets_at = resets_at
        _context = context.copy() if context else {}
        _context["resets_at"] = resets_at.strftime("%Y-%m-%dT%H:%M:%SZ")
        super().__init__(
            error_code=429120,
            message_key="claudeClient.claudeRateLimited",
            status_code=429,
            context=_context,
            retryable=True,
        )


class CloudflareBlockedError(AppError):
    def __init__(self, context: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code=503121,
            message_key="claudeClient.cloudflareBlocked",
            status_code=503,
            context=context,
        )


class OrganizationDisabledError(AppError):
    def __init__(self, context: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code=400122,
            message_key="claudeClient.organizationDisabled",
            status_code=400,
            context=context,
            retryable=True,
        )


class InvalidModelNameError(AppError):
    def __init__(self, model_name: str, context: Optional[Dict[str, Any]] = None):
        _context = context.copy() if context else {}
        _context["model_name"] = model_name
        super().__init__(
            error_code=400123,
            message_key="claudeClient.invalidModelName",
            status_code=400,
            context=_context,
        )


class ClaudeAuthenticationError(AppError):
    def __init__(self, context: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code=400124,
            message_key="claudeClient.authenticationError",
            status_code=400,
            context=context,
        )


class ClaudeHttpError(AppError):
    def __init__(
        self,
        url,
        status_code: int,
        error_type: str,
        error_message: Any,
        context: Optional[Dict[str, Any]] = None,
    ):
        _context = context.copy() if context else {}
        _context.update({
            "url": url,
            "status_code": status_code,
            "error_type": error_type,
            "error_message": error_message,
        })
        super().__init__(
            error_code=503130,
            message_key="claudeClient.httpError",
            status_code=status_code,
            context=_context,
            retryable=True,
        )


class NoValidMessagesError(AppError):
    def __init__(self, context: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code=400140,
            message_key="messageProcessor.noValidMessages",
            status_code=400,
            context=context,
        )


class ExternalImageDownloadError(AppError):
    def __init__(self, url: str, context: Optional[Dict[str, Any]] = None):
        _context = context.copy() if context else {}
        _context.update({"url": url})
        super().__init__(
            error_code=503141,
            message_key="messageProcessor.externalImageDownloadError",
            status_code=503,
            context=_context,
        )


class ExternalImageNotAllowedError(AppError):
    def __init__(self, url: str, context: Optional[Dict[str, Any]] = None):
        _context = context.copy() if context else {}
        _context.update({"url": url})
        super().__init__(
            error_code=400142,
            message_key="messageProcessor.externalImageNotAllowed",
            status_code=400,
            context=_context,
        )


class NoResponseError(AppError):
    def __init__(self, context: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code=503160,
            message_key="pipeline.noResponse",
            status_code=503,
            context=context,
        )


class OAuthExchangeError(AppError):
    def __init__(self, reason: str, context: Optional[Dict[str, Any]] = None):
        _context = context.copy() if context else {}
        _context["reason"] = reason or "Unknown"
        super().__init__(
            error_code=400180,
            message_key="oauthService.oauthExchangeError",
            status_code=400,
            context=_context,
        )


class OrganizationInfoError(AppError):
    def __init__(self, reason: str, context: Optional[Dict[str, Any]] = None):
        _context = context.copy() if context else {}
        _context["reason"] = reason or "Unknown"
        super().__init__(
            error_code=503181,
            message_key="oauthService.organizationInfoError",
            status_code=503,
            context=_context,
        )


class CookieAuthorizationError(AppError):
    def __init__(self, reason: str, context: Optional[Dict[str, Any]] = None):
        _context = context.copy() if context else {}
        _context["reason"] = reason or "Unknown"
        super().__init__(
            error_code=400182,
            message_key="oauthService.cookieAuthorizationError",
            status_code=400,
            context=_context,
        )


class OAuthAuthenticationNotAllowedError(AppError):
    def __init__(self, context: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code=400183,
            message_key="oauthService.oauthAuthenticationNotAllowed",
            status_code=400,
            context=context,
        )


class ClaudeStreamingError(AppError):
    def __init__(
        self,
        error_type: str,
        error_message: str,
        context: Optional[Dict[str, Any]] = None,
    ):
        _context = context.copy() if context else {}
        _context.update({
            "error_type": error_type,
            "error_message": error_message,
        })
        super().__init__(
            error_code=503500,
            message_key="processors.nonStreamingResponseProcessor.streamingError",
            status_code=503,
            context=_context,
            retryable=True,
        )


class NoMessageError(AppError):
    def __init__(self, context: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code=503501,
            message_key="processors.nonStreamingResponseProcessor.noMessage",
            status_code=503,
            context=context,
            retryable=True,
        )
