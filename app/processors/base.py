"""Base classes for request processing pipeline."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

from fastapi import Request
from fastapi.responses import StreamingResponse, JSONResponse


@dataclass
class BaseContext:
    """Base context passed between processors in the pipeline."""

    original_request: Request
    response: Optional[StreamingResponse | JSONResponse] = None
    metadata: dict = field(
        default_factory=dict
    )  # For storing custom data between processors


class BaseProcessor(ABC):
    """Base class for all request processors."""

    @abstractmethod
    async def process(self, context: BaseContext) -> BaseContext:
        """
        Process the request context.

        Args:
            context: The processing context

        Returns:
            Updated context.
        """
        pass

    @property
    def name(self) -> str:
        """Get the processor name."""
        return self.__class__.__name__
