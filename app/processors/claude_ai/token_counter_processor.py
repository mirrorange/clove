from typing import AsyncIterator
from loguru import logger
import tiktoken

from app.processors.base import BaseProcessor
from app.processors.claude_ai import ClaudeAIContext
from app.models.streaming import (
    MessageStartEvent,
    StreamingEvent,
    MessageDeltaEvent,
)
from app.models.claude import Usage
from app.utils.messages import process_messages

encoder = tiktoken.get_encoding("cl100k_base")


class TokenCounterProcessor(BaseProcessor):
    """Processor that estimates token usage when it's not provided by the API."""

    async def process(self, context: ClaudeAIContext) -> ClaudeAIContext:
        """
        Intercept MessageDeltaEvent and add token usage estimation if missing.

        Requires:
            - event_stream in context
            - messages_api_request in context (for input token counting)
            - collected_message in context (for output token counting)

        Produces:
            - event_stream with updated MessageDeltaEvent containing usage
        """
        if not context.event_stream:
            logger.warning("Skipping TokenCounterProcessor due to missing event_stream")
            return context

        if not context.messages_api_request:
            logger.warning(
                "Skipping TokenCounterProcessor due to missing messages_api_request"
            )
            return context

        logger.debug("Setting up token counting for stream")

        original_stream = context.event_stream
        new_stream = self._count_tokens_generator(original_stream, context)
        context.event_stream = new_stream

        return context

    async def _count_tokens_generator(
        self,
        event_stream: AsyncIterator[StreamingEvent],
        context: ClaudeAIContext,
    ) -> AsyncIterator[StreamingEvent]:
        """
        Generator that adds token usage to MessageDeltaEvent if missing.
        """
        # Pre-calculate input tokens once
        input_tokens = await self._calculate_input_tokens(context)

        async for event in event_stream:
            if (
                isinstance(event.root, MessageStartEvent)
                and not event.root.message.usage
            ):
                usage = Usage(
                    input_tokens=input_tokens,
                    output_tokens=1,
                    cache_creation_input_tokens=0,
                    cache_read_input_tokens=0,
                )

                event.root.message.usage = usage
                context.collected_message.usage = usage

                logger.debug(f"Added token usage estimation: input={input_tokens}")

            if isinstance(event.root, MessageDeltaEvent) and not event.root.usage:
                output_tokens = await self._calculate_output_tokens(context)

                usage = Usage(
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cache_creation_input_tokens=0,
                    cache_read_input_tokens=0,
                )

                event.root.usage = usage
                context.collected_message.usage = usage

                logger.debug(
                    f"Added token usage estimation: input={input_tokens}, output={output_tokens}"
                )

            yield event

    async def _calculate_input_tokens(self, context: ClaudeAIContext) -> int:
        """Calculate input tokens from the request messages."""
        if not context.messages_api_request:
            return 0

        merged_text, _ = await process_messages(
            context.messages_api_request.messages, context.messages_api_request.system
        )

        try:
            tokens = len(encoder.encode(merged_text, disallowed_special=()))
        except Exception:
            logger.warning("Tiktoken encoding failed for input, falling back to estimation")
            tokens = len(merged_text) // 4

        logger.debug(f"Calculated {tokens} input tokens")
        return tokens

    async def _calculate_output_tokens(self, context: ClaudeAIContext) -> int:
        """Calculate output tokens from the collected message."""
        if not context.collected_message:
            return 0

        merged_text, _ = await process_messages([context.collected_message])

        try:
            tokens = len(encoder.encode(merged_text, disallowed_special=()))
        except Exception:
            logger.warning("Tiktoken encoding failed for output, falling back to estimation")
            tokens = len(merged_text) // 4

        logger.debug(f"Calculated {tokens} output tokens")
        return tokens
