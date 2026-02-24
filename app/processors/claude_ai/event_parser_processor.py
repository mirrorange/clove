from loguru import logger

from app.processors.base import BaseProcessor
from app.processors.claude_ai import ClaudeAIContext
from app.services.event_processing.event_parser import EventParser


class EventParsingProcessor(BaseProcessor):
    """Processor that parses SSE streams into StreamingEvent objects."""

    def __init__(self):
        super().__init__()
        self.parser = EventParser()

    async def process(self, context: ClaudeAIContext) -> ClaudeAIContext:
        """
        Parse the original_stream into event_stream.

        Requires:
            - original_stream in context

        Produces:
            - event_stream in context
        """
        if context.event_stream:
            logger.debug("Skipping EventParsingProcessor due to existing event_stream")
            return context

        if not context.original_stream:
            logger.warning(
                "Skipping EventParsingProcessor due to missing original_stream"
            )
            return context

        logger.debug("Starting event parsing from SSE stream")
        context.event_stream = self.parser.parse_stream(context.original_stream)

        return context
