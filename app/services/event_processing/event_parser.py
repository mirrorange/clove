import json
from typing import AsyncIterator, Optional
from dataclasses import dataclass
from loguru import logger

from pydantic import ValidationError

from app.models.streaming import (
    StreamingEvent,
    UnknownEvent,
)


@dataclass
class SSEMessage:
    event: Optional[str] = None
    data: Optional[str] = None


class EventParser:
    """Parses SSE (Server-Sent Events) streams into StreamingEvent objects."""

    def __init__(self, skip_unknown_events: bool = True):
        self.skip_unknown_events = skip_unknown_events
        self.buffer = ""

    async def parse_stream(
        self, stream: AsyncIterator[str]
    ) -> AsyncIterator[StreamingEvent]:
        """
        Parse an SSE stream and yield StreamingEvent objects.

        Args:
            stream: AsyncIterator that yields string chunks from the SSE stream

        Yields:
            StreamingEvent objects parsed from the stream
        """
        async for chunk in stream:
            chunk = chunk.replace('\r\n', '\n') # Normalize line endings
            self.buffer += chunk

            async for event in self._process_buffer():
                logger.debug(f"Parsed event:\n{event.model_dump()}")
                yield event

        async for event in self.flush():
            yield event

    async def _process_buffer(self) -> AsyncIterator[StreamingEvent]:
        """Process the buffer and yield complete SSE messages as StreamingEvent objects."""
        while "\n\n" in self.buffer:
            message_end = self.buffer.index("\n\n")
            message_text = self.buffer[:message_end]
            self.buffer = self.buffer[message_end + 2 :]

            sse_msg = self._parse_sse_message(message_text)

            if sse_msg.data:
                event = self._create_streaming_event(sse_msg)
                if event:
                    yield event

    def _parse_sse_message(self, message_text: str) -> SSEMessage:
        """Parse a single SSE message from text."""
        sse_msg = SSEMessage()

        for line in message_text.split("\n"):
            if not line:
                continue

            if ":" not in line:
                field = line
                value = ""
            else:
                field, value = line.split(":", 1)
                if value.startswith(" "):
                    value = value[1:]

            if field == "event":
                sse_msg.event = value
            elif field == "data":
                if sse_msg.data is None:
                    sse_msg.data = value
                else:
                    sse_msg.data += "\n" + value

        return sse_msg

    def _create_streaming_event(self, sse_msg: SSEMessage) -> Optional[StreamingEvent]:
        """
        Create a StreamingEvent from an SSE message.

        Args:
            sse_msg: The parsed SSE message

        Returns:
            StreamingEvent object or None if parsing fails
        """
        try:
            data = json.loads(sse_msg.data)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON data: {e}")
            logger.debug(f"Raw data: {sse_msg.data}")
            return None

        try:
            streaming_event = StreamingEvent(root=data)
        except ValidationError:
            if self.skip_unknown_events:
                logger.debug(f"Skipping unknown event: {sse_msg.event}")
                return None
            logger.warning(
                "Failed to validate streaming event. Falling back to UnknownEvent."
            )
            logger.debug(f"Event data: {data}")
            streaming_event = StreamingEvent(
                root=UnknownEvent(type=sse_msg.event, data=data)
            )

        return streaming_event

    async def flush(self) -> AsyncIterator[StreamingEvent]:
        """
        Flush any remaining data in the buffer.

        This should be called when the stream ends to process any incomplete messages.

        Yields:
            Any remaining StreamingEvent objects
        """
        if self.buffer.strip():
            logger.warning(f"Flushing incomplete buffer: {self.buffer[:100]}...")

            self.buffer += "\n\n"

            async for event in self._process_buffer():
                yield event
