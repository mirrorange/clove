from typing import List, Optional
from loguru import logger

from app.services.session import session_manager
from app.processors.pipeline import ProcessingPipeline
from app.processors.base import BaseProcessor
from app.processors.claude_ai import ClaudeAIContext
from app.processors.claude_ai.tavern_test_message_processor import TestMessageProcessor
from app.processors.claude_ai.claude_web_processor import ClaudeWebProcessor
from app.processors.claude_ai.claude_api_processor import ClaudeAPIProcessor
from app.processors.claude_ai.event_parser_processor import EventParsingProcessor
from app.processors.claude_ai.streaming_response_processor import (
    StreamingResponseProcessor,
)
from app.processors.claude_ai.message_collector_processor import (
    MessageCollectorProcessor,
)
from app.processors.claude_ai.non_streaming_response_processor import (
    NonStreamingResponseProcessor,
)
from app.processors.claude_ai.token_counter_processor import TokenCounterProcessor
from app.processors.claude_ai.tool_result_processor import ToolResultProcessor
from app.processors.claude_ai.tool_call_event_processor import ToolCallEventProcessor
from app.processors.claude_ai.stop_sequences_processor import StopSequencesProcessor
from app.processors.claude_ai.model_injector_processor import ModelInjectorProcessor


class ClaudeAIPipeline(ProcessingPipeline):
    def __init__(self, processors: Optional[List[BaseProcessor]] = None):
        """
        Initialize the pipeline with processors.

        Args:
            processors: List of processors to use. If None, default processors are used.
        """
        processors = (
            [
                TestMessageProcessor(),
                ToolResultProcessor(),
                ClaudeAPIProcessor(),
                ClaudeWebProcessor(),
                EventParsingProcessor(),
                ModelInjectorProcessor(),
                StopSequencesProcessor(),
                ToolCallEventProcessor(),
                MessageCollectorProcessor(),
                TokenCounterProcessor(),
                StreamingResponseProcessor(),
                NonStreamingResponseProcessor(),
            ]
            if processors is None
            else processors
        )

        super().__init__(processors)

    async def process(
        self,
        context: ClaudeAIContext,
    ) -> ClaudeAIContext:
        """
        Process a Claude API request through the pipeline.

        Args:
            context: The processing context

        Returns:
            Updated context.

        Raises:
            Exception: If any processor fails or no response is generated
        """
        try:
            return await super().process(context)
        except Exception as e:
            if context.claude_session:
                await session_manager.remove_session(context.claude_session.session_id)
            logger.error(f"Pipeline processing failed: {e}")
            raise e
