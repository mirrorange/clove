from typing import AsyncIterator
from loguru import logger

from app.processors.base import BaseProcessor
from app.processors.claude_ai import ClaudeAIContext
from app.models.streaming import (
    MessageStartEvent,
    StreamingEvent,
)


class ModelInjectorProcessor(BaseProcessor):
    """Processor that injects model information when it's missing from MessageStartEvent."""

    async def process(self, context: ClaudeAIContext) -> ClaudeAIContext:
        """
        Intercept MessageStartEvent and add model information if missing.

        Requires:
            - event_stream in context
            - messages_api_request in context (for model information)

        Produces:
            - event_stream with updated MessageStartEvent containing model
        """
        if not context.event_stream:
            logger.warning(
                "Skipping ModelInjectorProcessor due to missing event_stream"
            )
            return context

        if not context.messages_api_request:
            logger.warning(
                "Skipping ModelInjectorProcessor due to missing messages_api_request"
            )
            return context

        logger.debug("Setting up model injection for stream")

        original_stream = context.event_stream
        new_stream = self._inject_model_generator(original_stream, context)
        context.event_stream = new_stream

        return context

    async def _inject_model_generator(
        self,
        event_stream: AsyncIterator[StreamingEvent],
        context: ClaudeAIContext,
    ) -> AsyncIterator[StreamingEvent]:
        """
        Generator that adds model to MessageStartEvent if missing.
        """
        # Get model from request
        model = context.messages_api_request.model

        async for event in event_stream:
            if isinstance(event.root, MessageStartEvent):
                # Check if model is missing or empty
                if not event.root.message.model:
                    event.root.message.model = model
                    logger.debug(f"Injected model '{model}' into MessageStartEvent")
                else:
                    logger.debug(
                        f"MessageStartEvent already has model: '{event.root.message.model}'"
                    )

            yield event
