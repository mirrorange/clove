import json5
from typing import AsyncIterator
from loguru import logger

from app.processors.base import BaseProcessor
from app.processors.claude_ai import ClaudeAIContext
from app.models.streaming import (
    Delta,
    StreamingEvent,
    MessageStartEvent,
    ContentBlockStartEvent,
    ContentBlockDeltaEvent,
    ContentBlockStopEvent,
    MessageDeltaEvent,
    MessageStopEvent,
    ErrorEvent,
    ErrorInfo,
    TextDelta,
    InputJsonDelta,
    ThinkingDelta,
)
from app.models.claude import (
    ContentBlock,
    ServerToolUseContent,
    TextContent,
    ThinkingContent,
    ToolResultContent,
    ToolUseContent,
)


class MessageCollectorProcessor(BaseProcessor):
    """Processor that collects streaming events into a Message object without consuming the stream."""

    async def process(self, context: ClaudeAIContext) -> ClaudeAIContext:
        """
        Collect streaming events into a Message object and update it in real-time.
        This processor runs for both streaming and non-streaming requests.

        Requires:
            - event_stream in context

        Produces:
            - collected_message in context (updated in real-time)
            - event_stream in context (wrapped to collect messages without consuming)
        """
        if not context.event_stream:
            logger.warning(
                "Skipping MessageCollectorProcessor due to missing event_stream"
            )
            return context

        logger.debug("Setting up message collection from stream")

        original_stream = context.event_stream

        new_stream = self._collect_messages_generator(original_stream, context)
        context.event_stream = new_stream

        return context

    async def _collect_messages_generator(
        self, event_stream: AsyncIterator[StreamingEvent], context: ClaudeAIContext
    ) -> AsyncIterator[StreamingEvent]:
        """
        Generator that collects messages from the stream without consuming events.
        Updates context.collected_message in real-time.
        """
        context.collected_message = None

        async for event in event_stream:
            # Process the event to build/update the message
            if isinstance(event.root, MessageStartEvent):
                context.collected_message = event.root.message.model_copy(deep=True)
                logger.debug(f"Message started: {context.collected_message.id}")

            elif isinstance(event.root, ContentBlockStartEvent):
                if context.collected_message:
                    while len(context.collected_message.content) <= event.root.index:
                        context.collected_message.content.append(None)
                    context.collected_message.content[event.root.index] = (
                        event.root.content_block.model_copy(deep=True)
                    )
                    logger.debug(
                        f"Content block {event.root.index} started: {event.root.content_block.type}"
                    )

            elif isinstance(event.root, ContentBlockDeltaEvent):
                if context.collected_message and event.root.index < len(
                    context.collected_message.content
                ):
                    self._apply_delta(
                        context.collected_message.content[event.root.index],
                        event.root.delta,
                    )

            elif isinstance(event.root, ContentBlockStopEvent):
                # Boundary checking to prevent IndexError caused by refusal responses
                if (
                    context.collected_message
                    and event.root.index < len(context.collected_message.content)
                ):
                    block = context.collected_message.content[event.root.index]
                    if isinstance(block, (ToolUseContent, ServerToolUseContent)):
                        if hasattr(block, "input_json") and block.input_json:
                            block.input = json5.loads(block.input_json)
                            del block.input_json
                    if isinstance(block, ToolResultContent):
                        if hasattr(block, "content_json") and block.content_json:
                            block = ToolResultContent(
                                **block.model_dump(exclude={"content"}),
                                content=json5.loads(block.content_json),
                            )
                            del block.content_json
                            context.collected_message.content[event.root.index] = block
                    logger.debug(f"Content block {event.root.index} stopped")
                else:
                    logger.debug(
                        f"Content block {event.root.index} stop skipped (no corresponding start)"
                    )

            elif isinstance(event.root, MessageDeltaEvent):
                if context.collected_message and event.root.delta:
                    if event.root.delta.stop_reason:
                        context.collected_message.stop_reason = (
                            event.root.delta.stop_reason
                        )
                        # When refusal is detected and content is empty, yield ErrorEvent
                        if (
                            event.root.delta.stop_reason == "refusal"
                            and not context.collected_message.content
                        ):
                            logger.warning("Request refused by Claude's safety filter")
                            error_event = StreamingEvent(
                                root=ErrorEvent(
                                    type="error",
                                    error=ErrorInfo(
                                        type="refusal",
                                        message="Chat paused: Claude's safety filters flagged this message. This occasionally happens with normal, safe messages. Try rephrasing or using a different model."
                                    )
                                )
                            )
                            yield error_event
                    if event.root.delta.stop_sequence:
                        context.collected_message.stop_sequence = (
                            event.root.delta.stop_sequence
                        )
                if context.collected_message and event.root.usage:
                    context.collected_message.usage = event.root.usage

            elif isinstance(event.root, MessageStopEvent):
                if context.collected_message:
                    context.collected_message.content = [
                        block
                        for block in context.collected_message.content
                        if block is not None
                    ]
                    logger.debug(
                        f"Message stopped with {len(context.collected_message.content)} content blocks"
                    )

            elif isinstance(event.root, ErrorEvent):
                logger.warning(f"Error event received: {event.root.error.message}")

            # Yield the event without modification
            yield event

        if context.collected_message:
            logger.debug(
                f"Collected message:\n{context.collected_message.model_dump()}"
            )

    def _apply_delta(self, content_block: ContentBlock, delta: Delta) -> None:
        """Apply a delta to a content block."""
        if isinstance(delta, TextDelta):
            if isinstance(content_block, TextContent):
                content_block.text += delta.text
        elif isinstance(delta, ThinkingDelta):
            if isinstance(content_block, ThinkingContent):
                content_block.thinking += delta.thinking
        elif isinstance(delta, InputJsonDelta):
            if isinstance(content_block, (ToolUseContent, ServerToolUseContent)):
                if hasattr(content_block, "input_json"):
                    content_block.input_json += delta.partial_json
                else:
                    content_block.input_json = delta.partial_json
            if isinstance(content_block, ToolResultContent):
                if hasattr(content_block, "content_json"):
                    content_block.content_json += delta.partial_json
                else:
                    content_block.content_json = delta.partial_json
