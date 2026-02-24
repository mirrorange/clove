from loguru import logger
from tenacity import RetryCallState

from app.core.exceptions import AppError


def is_retryable_error(exception):
    """Check if the exception is an AppError with retryable=True"""
    return isinstance(exception, AppError) and exception.retryable


def log_before_sleep(retry_state: RetryCallState) -> None:
    """Custom before_sleep callback that safely logs retry attempts."""
    attempt_number = retry_state.attempt_number
    exception = retry_state.outcome.exception() if retry_state.outcome else None

    if exception:
        exception_type = type(exception).__name__
        logger.warning(
            f"Retrying {retry_state.fn.__name__} after attempt {attempt_number} "
            f"due to {exception_type}: {str(exception)}"
        )

    else:
        logger.warning(
            f"Retrying {retry_state.fn.__name__} after attempt {attempt_number}"
        )
