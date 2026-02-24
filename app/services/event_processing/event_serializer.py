import json
from typing import AsyncIterator, Optional

from app.models.streaming import StreamingEvent, UnknownEvent


class EventSerializer:
    """Serializes StreamingEvent objects into SSE (Server-Sent Events) format."""

    def __init__(self, skip_unknown_events: bool = True):
        self.skip_unknown_events = skip_unknown_events

    async def serialize_stream(
        self, events: AsyncIterator[StreamingEvent]
    ) -> AsyncIterator[str]:
        """
        Serialize a stream of StreamingEvent objects into SSE format.

        Args:
            events: AsyncIterator that yields StreamingEvent objects

        Yields:
            String chunks in SSE format
        """
        async for event in events:
            sse_message = self.serialize_event(event)
            if sse_message:
                yield sse_message

    def serialize_event(self, event: StreamingEvent) -> Optional[str]:
        """
        Serialize a single StreamingEvent into SSE format.

        Args:
            event: StreamingEvent object to serialize

        Returns:
            SSE formatted string or None if serialization fails
        """
        if isinstance(event.root, UnknownEvent):
            if self.skip_unknown_events:
                return None
            json_data = json.dumps(
                event.root.data, ensure_ascii=False, separators=(",", ":")
            )
        else:
            json_data = event.model_dump_json(exclude_none=True)

        sse_parts = []

        if event.root.type:
            sse_parts.append(f"event: {event.root.type}")

        data_lines = json_data.split("\n")
        for line in data_lines:
            sse_parts.append(f"data: {line}")

        sse_message = "\n".join(sse_parts) + "\n\n"

        return sse_message

    async def serialize_batch(self, events: list[StreamingEvent]) -> str:
        """
        Serialize a batch of StreamingEvent objects into a single SSE string.

        Args:
            events: List of StreamingEvent objects to serialize

        Returns:
            Concatenated SSE formatted string
        """
        result_parts = []

        for event in events:
            sse_message = self.serialize_event(event)
            if sse_message:
                result_parts.append(sse_message)

        return "".join(result_parts)
