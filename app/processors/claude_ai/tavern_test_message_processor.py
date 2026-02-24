from loguru import logger
import uuid

from fastapi.responses import JSONResponse

from app.processors.base import BaseProcessor
from app.processors.claude_ai import ClaudeAIContext
from app.models.claude import (
    Message,
    Role,
    TextContent,
    Usage,
)


class TestMessageProcessor(BaseProcessor):
    """Processor that handles test messages."""

    async def process(self, context: ClaudeAIContext) -> ClaudeAIContext:
        """
        Check if this is a test message and respond immediately if so.

        Test message criteria:
        - Only one message in messages array
        - Message role is "user"
        - Message content is "Hi"
        - stream is False

        If it's a test message, creates a MessagesAPIResponse and stops the pipeline.
        """
        if not context.messages_api_request:
            return context

        request = context.messages_api_request

        if (
            len(request.messages) == 1
            and request.messages[0].role == Role.USER
            and request.stream is False
            and (
                (
                    isinstance(request.messages[0].content, str)
                    and request.messages[0].content == "Hi"
                )
                or (
                    isinstance(request.messages[0].content, list)
                    and len(request.messages[0].content) == 1
                    and isinstance(request.messages[0].content[0], TextContent)
                    and request.messages[0].content[0].text == "Hi"
                )
            )
        ):
            logger.debug("Test message detected, returning canned response")

            response = Message(
                id=f"msg_{uuid.uuid4().hex[:10]}",
                type="message",
                role="assistant",
                content=[
                    TextContent(type="text", text="Hello! How can I assist you today?")
                ],
                model=request.model,
                stop_reason="end_turn",
                stop_sequence=None,
                usage=Usage(input_tokens=1, output_tokens=9),
            )

            context.response = JSONResponse(
                content=response.model_dump(), status_code=200
            )

            context.metadata["stop_pipeline"] = True
            return context

        return context
