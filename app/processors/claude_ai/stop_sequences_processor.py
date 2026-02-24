from typing import AsyncIterator, List
from loguru import logger

from app.processors.base import BaseProcessor
from app.processors.claude_ai import ClaudeAIContext
from app.models.streaming import (
    StreamingEvent,
    ContentBlockDeltaEvent,
    ContentBlockStopEvent,
    MessageDeltaEvent,
    MessageStopEvent,
    MessageDeltaData,
    TextDelta,
)
from app.services.session import session_manager


class StopSequencesProcessor(BaseProcessor):
    """Processor that handles stop sequences in streaming responses."""

    async def process(self, context: ClaudeAIContext) -> ClaudeAIContext:
        """
        Process streaming events to detect and handle stop sequences.

        Requires:
            - event_stream in context
            - messages_api_request in context (for stop_sequences)

        Produces:
            - Modified event_stream that stops when a stop sequence is detected
            - Injects MessageDelta and MessageStop events when stop sequence found
        """
        if not context.event_stream:
            logger.warning(
                "Skipping StopSequencesProcessor due to missing event_stream"
            )
            return context

        if not context.messages_api_request:
            logger.warning(
                "Skipping StopSequencesProcessor due to missing messages_api_request"
            )
            return context

        stop_sequences = context.messages_api_request.stop_sequences
        if not stop_sequences:
            logger.debug("No stop sequences configured, skipping processor")
            return context

        logger.debug(f"Setting up stop sequences processing for: {stop_sequences}")

        original_stream = context.event_stream
        new_stream = self._process_stop_sequences(
            original_stream, stop_sequences, context
        )
        context.event_stream = new_stream

        return context

    async def _process_stop_sequences(
        self,
        event_stream: AsyncIterator[StreamingEvent],
        stop_sequences: List[str],
        context: ClaudeAIContext,
    ) -> AsyncIterator[StreamingEvent]:
        """
        Process events and stop when a stop sequence is detected.
        Uses incremental matching with buffering.
        """
        stop_sequences_set = set(stop_sequences)

        buffer = ""
        current_index = 0

        # Track potential matches: (start_position, current_matched_text)
        potential_matches = []

        async for event in event_stream:
            if isinstance(event.root, ContentBlockDeltaEvent) and isinstance(
                event.root.delta, TextDelta
            ):
                text = event.root.delta.text
                current_index = event.root.index

                for char in text:
                    buffer += char
                    current_pos = len(buffer) - 1

                    potential_matches.append((current_pos, ""))

                    new_matches = []
                    for start_pos, matched_text in potential_matches:
                        extended_match = matched_text + char

                        could_match = False
                        for stop_seq in stop_sequences:
                            if stop_seq.startswith(extended_match):
                                could_match = True
                                break

                        if could_match:
                            new_matches.append((start_pos, extended_match))

                            if extended_match in stop_sequences_set:
                                logger.debug(
                                    f"Stop sequence detected: '{extended_match}'"
                                )

                                safe_text = buffer[:start_pos]

                                if safe_text:
                                    yield StreamingEvent(
                                        root=ContentBlockDeltaEvent(
                                            type="content_block_delta",
                                            index=current_index,
                                            delta=TextDelta(
                                                type="text_delta", text=safe_text
                                            ),
                                        )
                                    )

                                yield StreamingEvent(
                                    root=ContentBlockStopEvent(
                                        type="content_block_stop", index=current_index
                                    )
                                )

                                yield StreamingEvent(
                                    root=MessageDeltaEvent(
                                        type="message_delta",
                                        delta=MessageDeltaData(
                                            stop_reason="stop_sequence",
                                            stop_sequence=extended_match,
                                        ),
                                        usage=None,
                                    )
                                )

                                yield StreamingEvent(
                                    root=MessageStopEvent(type="message_stop")
                                )

                                if context.claude_session:
                                    await session_manager.remove_session(
                                        context.claude_session.session_id
                                    )

                                return

                    potential_matches = new_matches

                    if potential_matches:
                        earliest_start = min(
                            start_pos for start_pos, _ in potential_matches
                        )
                        safe_length = earliest_start
                    else:
                        safe_length = len(buffer)

                    if safe_length > 0:
                        safe_text = buffer[:safe_length]
                        yield StreamingEvent(
                            root=ContentBlockDeltaEvent(
                                type="content_block_delta",
                                index=current_index,
                                delta=TextDelta(type="text_delta", text=safe_text),
                            )
                        )

                        buffer = buffer[safe_length:]
                        new_matches = []
                        for start_pos, matched_text in potential_matches:
                            new_start = start_pos - safe_length
                            if new_start >= 0:
                                new_matches.append((new_start, matched_text))
                        potential_matches = new_matches

            else:
                # Non-text event - flush buffer and reset
                if buffer:
                    yield StreamingEvent(
                        root=ContentBlockDeltaEvent(
                            type="content_block_delta",
                            index=current_index,
                            delta=TextDelta(type="text_delta", text=buffer),
                        )
                    )
                    buffer = ""
                    potential_matches = []

                yield event
