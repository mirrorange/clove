from loguru import logger

from fastapi.responses import StreamingResponse

from app.processors.base import BaseProcessor
from app.processors.claude_ai import ClaudeAIContext
from app.services.event_processing.event_serializer import EventSerializer


class StreamingResponseProcessor(BaseProcessor):
    """Processor that serializes event streams and creates a StreamingResponse."""

    def __init__(self):
        super().__init__()
        self.serializer = EventSerializer()

    async def process(self, context: ClaudeAIContext) -> ClaudeAIContext:
        """
        Serialize the event_stream and create a StreamingResponse.

        Requires:
            - event_stream in context

        Produces:
            - response in context

        This processor typically marks the end of the pipeline by returning STOP action.
        """
        if context.response:
            logger.debug("Skipping StreamingResponseProcessor due to existing response")
            return context

        if not context.event_stream:
            logger.warning(
                "Skipping StreamingResponseProcessor due to missing event_stream"
            )
            return context

        if (
            not context.messages_api_request
            or context.messages_api_request.stream is not True
        ):
            logger.debug(
                "Skipping StreamingResponseProcessor due to non-streaming request"
            )
            return context

        logger.info("Creating streaming response from event stream")

        sse_stream = self.serializer.serialize_stream(context.event_stream)

        context.response = StreamingResponse(
            sse_stream,
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable nginx buffering
            },
        )

        return context
