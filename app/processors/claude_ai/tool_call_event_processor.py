from typing import AsyncIterator, Optional
from loguru import logger

from app.processors.base import BaseProcessor
from app.processors.claude_ai import ClaudeAIContext
from app.models.streaming import (
    StreamingEvent,
    ContentBlockStartEvent,
    ContentBlockStopEvent,
    MessageDeltaEvent,
    MessageStopEvent,
    MessageDeltaData,
)
from app.models.claude import ToolResultContent, ToolUseContent
from app.services.tool_call import tool_call_manager


class ToolCallEventProcessor(BaseProcessor):
    """Processor that handles tool use events in the streaming response."""

    async def process(self, context: ClaudeAIContext) -> ClaudeAIContext:
        """
        Intercept tool use content blocks and inject MessageDelta/MessageStop events.

        Requires:
            - event_stream in context
            - cladue_session in context

        Produces:
            - Modified event_stream with injected events for tool calls
            - Pauses session when tool call is detected
        """
        if not context.event_stream:
            logger.warning(
                "Skipping ToolCallEventProcessor due to missing event_stream"
            )
            return context

        if not context.claude_session:
            logger.warning("Skipping ToolCallEventProcessor due to missing session")
            return context

        logger.debug("Setting up tool call event processing")

        original_stream = context.event_stream
        new_stream = self._process_tool_events(original_stream, context)
        context.event_stream = new_stream

        return context

    async def _process_tool_events(
        self,
        event_stream: AsyncIterator[StreamingEvent],
        context: ClaudeAIContext,
    ) -> AsyncIterator[StreamingEvent]:
        """
        Process events and inject MessageDelta/MessageStop when tool use is detected.
        """
        current_tool_use_id: Optional[str] = None
        tool_use_detected = False
        content_block_index: Optional[int] = None
        tool_result_detected = False

        async for event in event_stream:
            # Check for ContentBlockStartEvent with tool_use type
            if isinstance(event.root, ContentBlockStartEvent):
                if isinstance(event.root.content_block, ToolUseContent):
                    current_tool_use_id = event.root.content_block.id
                    content_block_index = event.root.index
                    tool_use_detected = True
                    logger.debug(
                        f"Detected tool use start: {current_tool_use_id} "
                        f"(name: {event.root.content_block.name})"
                    )
                elif isinstance(event.root.content_block, ToolResultContent):
                    logger.debug(
                        f"Detected tool result: {event.root.content_block.tool_use_id}"
                    )
                    tool_result_detected = True

            # Yield the original event
            if tool_result_detected:
                logger.debug("Skipping tool result content block")
            else:
                yield event

            # Check for ContentBlockStopEvent for a tool use block
            if isinstance(event.root, ContentBlockStopEvent):
                if tool_result_detected:
                    logger.debug("Tool result block ended")
                    tool_result_detected = False
                if (
                    tool_use_detected
                    and content_block_index is not None
                    and event.root.index == content_block_index
                ):
                    logger.debug(f"Tool use block ended: {current_tool_use_id}")

                    message_delta = MessageDeltaEvent(
                        type="message_delta",
                        delta=MessageDeltaData(stop_reason="tool_use"),
                        usage=None,
                    )
                    yield StreamingEvent(root=message_delta)

                    message_stop = MessageStopEvent(type="message_stop")
                    yield StreamingEvent(root=message_stop)

                    # Register the tool call
                    if current_tool_use_id and context.claude_session:
                        tool_call_manager.register_tool_call(
                            tool_use_id=current_tool_use_id,
                            session_id=context.claude_session.session_id,
                            message_id=context.collected_message.id
                            if context.collected_message
                            else None,
                        )

                        logger.info(
                            f"Registered tool call {current_tool_use_id} for session {context.claude_session.session_id}"
                        )

                    current_tool_use_id = None
                    tool_use_detected = False
                    content_block_index = None

                    break
