import uuid
from loguru import logger

from app.processors.base import BaseProcessor
from app.processors.claude_ai import ClaudeAIContext
from app.models.claude import TextContent, ToolResultContent
from app.models.streaming import MessageStartEvent, StreamingEvent
from app.services.tool_call import tool_call_manager
from app.services.session import session_manager
from app.services.event_processing import EventSerializer

event_serializer = EventSerializer()


class ToolResultProcessor(BaseProcessor):
    """Processor that handles tool result messages and resumes paused sessions."""

    async def process(self, context: ClaudeAIContext) -> ClaudeAIContext:
        """
        Check if the last message is a tool result and handle accordingly.

        Requires:
            - messages_api_request in context

        Produces:
            - Resumes paused session if tool result matches
            - Sets event_stream from resumed session
            - Skips normal request building/sending
        """
        if not context.messages_api_request:
            logger.warning(
                "Skipping ToolResultProcessor due to missing messages_api_request"
            )
            return context

        messages = context.messages_api_request.messages
        if not messages:
            return context

        last_message = messages[-1]

        if last_message.role != "user":
            return context

        if isinstance(last_message.content, str):
            return context

        # Find tool result content block
        lsat_content_block = last_message.content[-1]
        if not isinstance(lsat_content_block, ToolResultContent):
            return context

        tool_result = lsat_content_block

        logger.debug(f"Found tool result for tool_use_id: {tool_result.tool_use_id}")

        # Check if we have a pending tool call for this ID
        tool_call_state = tool_call_manager.get_tool_call(tool_result.tool_use_id)
        if not tool_call_state:
            logger.debug(
                f"No pending tool call found for tool_use_id: {tool_result.tool_use_id}"
            )
            return context

        # Get the session
        session = await session_manager.get_session(tool_call_state.session_id)
        if not session:
            logger.error(
                f"Session {tool_call_state.session_id} not found for tool call {tool_result.tool_use_id}"
            )
            tool_call_manager.complete_tool_call(tool_result.tool_use_id)
            return context

        if isinstance(tool_result.content, str):
            tool_result.content = [TextContent(type="text", text=tool_result.content)]
        tool_result_payload = tool_result.model_dump()

        await session.send_tool_result(tool_result_payload)
        logger.info(
            f"Sent tool result for {tool_result.tool_use_id} to session {session.session_id}"
        )

        if not session.sse_stream:
            logger.error(f"No stream available for session {session.session_id}")
            tool_call_manager.complete_tool_call(tool_result.tool_use_id)
            return context

        # Continue with the existing stream
        resumed_stream = session.sse_stream

        message_start_event = MessageStartEvent(
            type="message_start",
            message=context.collected_message
            if context.collected_message
            else {
                "id": tool_call_state.message_id or str(uuid.uuid4()),
                "type": "message",
                "role": "assistant",
                "content": [],
                "model": context.messages_api_request.model,
            },
        )

        # Create a generator that yields the message start event followed by the resumed stream
        async def resumed_event_stream():
            yield event_serializer.serialize_event(
                StreamingEvent(root=message_start_event)
            )
            async for event in resumed_stream:
                yield event

        context.original_stream = resumed_event_stream()
        context.claude_session = session

        tool_call_manager.complete_tool_call(tool_result.tool_use_id)

        # Skip the normal Claude AI processor
        context.metadata["skip_processors"] = [
            "ClaudeAPIProcessor",
            "ClaudeWebProcessor",
        ]

        return context
