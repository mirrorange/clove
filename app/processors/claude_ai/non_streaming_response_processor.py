from loguru import logger
from fastapi.responses import JSONResponse

from app.core.exceptions import ClaudeStreamingError, NoMessageError
from app.models.streaming import ErrorEvent
from app.processors.base import BaseProcessor
from app.processors.claude_ai import ClaudeAIContext


class NonStreamingResponseProcessor(BaseProcessor):
    """Processor that builds a non-streaming JSON response from collected message."""

    async def process(self, context: ClaudeAIContext) -> ClaudeAIContext:
        """
        Build a non-streaming JSON response from the collected message.
        This processor only runs for non-streaming requests.

        Requires:
            - messages_api_request with stream=False
            - collected_message in context (must consume entire stream first)

        Produces:
            - response (JSONResponse) in context
        """
        if context.response:
            logger.debug(
                "Skipping NonStreamingResponseProcessor due to existing response"
            )
            return context

        if context.messages_api_request and context.messages_api_request.stream is True:
            logger.debug("Skipping NonStreamingResponseProcessor for streaming request")
            return context

        if not context.event_stream:
            logger.warning(
                "Skipping NonStreamingResponseProcessor due to missing event_stream"
            )
            return context

        logger.info("Building non-streaming response")

        # Consume the entire stream to ensure collected_message is complete
        async for event in context.event_stream:
            if isinstance(event.root, ErrorEvent):
                raise ClaudeStreamingError(
                    error_type=event.root.error.type,
                    error_message=event.root.error.message,
                )

        if not context.collected_message:
            logger.error("No message collected after consuming stream")
            raise NoMessageError()

        context.response = JSONResponse(
            content=context.collected_message.model_dump(exclude_none=True),
            headers={
                "Content-Type": "application/json",
                "Cache-Control": "no-cache",
            },
        )

        return context
