from dataclasses import dataclass
from typing import Optional, AsyncIterator

from app.core.claude_session import ClaudeWebSession
from app.models.claude import Message, MessagesAPIRequest
from app.models.internal import ClaudeWebRequest
from app.models.streaming import StreamingEvent
from app.processors.base import BaseContext


@dataclass
class ClaudeAIContext(BaseContext):
    messages_api_request: Optional[MessagesAPIRequest] = None
    claude_web_request: Optional[ClaudeWebRequest] = None
    claude_session: Optional[ClaudeWebSession] = None
    original_stream: Optional[AsyncIterator[str]] = None
    event_stream: Optional[AsyncIterator[StreamingEvent]] = None
    collected_message: Optional[Message] = None
