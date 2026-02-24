from typing import Dict, Any, AsyncIterator, Optional
from datetime import datetime
from app.core.http_client import Response
from loguru import logger

from app.core.config import settings
from app.core.external.claude_client import ClaudeWebClient
from app.services.account import account_manager


class ClaudeWebSession:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.last_activity = datetime.now()
        self.conv_uuid: Optional[str] = None
        self.paprika_mode: Optional[str] = None
        self.sse_stream: Optional[AsyncIterator[str]] = None

    async def initialize(self):
        """Initialize the session."""
        self.account = await account_manager.get_account_for_session(self.session_id)
        self.client = ClaudeWebClient(self.account)
        await self.client.initialize()

    async def stream(self, response: Response) -> AsyncIterator[str]:
        """Get the SSE stream."""
        buffer = b""
        async for chunk in response.aiter_bytes():
            self.update_activity()
            buffer += chunk
            lines = buffer.split(b"\n")
            buffer = lines[-1]
            for line in lines[:-1]:
                yield line.decode("utf-8") + "\n"

        if buffer:
            yield buffer.decode("utf-8")

        logger.debug(f"Stream completed for session {self.session_id}")

        from app.services.session import session_manager

        await session_manager.remove_session(self.session_id)

    async def cleanup(self):
        """Cleanup session resources."""
        logger.debug(f"Cleaning up session {self.session_id}")

        # Delete conversation if exists
        if self.conv_uuid and not settings.preserve_chats:
            await self.client.delete_conversation(self.conv_uuid)

        await account_manager.release_session(self.session_id)
        await self.client.cleanup()

    async def _ensure_conversation_initialized(self) -> None:
        """Ensure conversation is initialized. Create if not exists."""
        if not self.conv_uuid:
            conv_uuid, paprika_mode = await self.client.create_conversation()
            self.conv_uuid = conv_uuid
            self.paprika_mode = paprika_mode

    def update_activity(self):
        """Update last activity timestamp."""
        self.last_activity = datetime.now()

    async def send_message(self, payload: Dict[str, Any]) -> AsyncIterator[str]:
        """Process a completion request through the pipeline."""
        self.update_activity()

        await self._ensure_conversation_initialized()

        response = await self.client.send_message(
            payload,
            conv_uuid=self.conv_uuid,
        )
        self.sse_stream = self.stream(response)

        logger.debug(f"Sent message for session {self.session_id}")
        return self.sse_stream

    async def upload_file(
        self, file_data: bytes, filename: str, content_type: str
    ) -> str:
        """Upload a file and return file UUID."""
        return await self.client.upload_file(file_data, filename, content_type)

    async def send_tool_result(self, payload: Dict[str, Any]) -> None:
        """Send tool result to Claude.ai."""
        if not self.conv_uuid:
            raise ValueError(
                "Session must have an active conversation to send tool results"
            )

        await self.client.send_tool_result(payload, self.conv_uuid)

    async def set_paprika_mode(self, mode: Optional[str]) -> None:
        """Set the conversation mode."""
        await self._ensure_conversation_initialized()

        if self.paprika_mode == mode:
            return

        await self.client.set_paprika_mode(self.conv_uuid, mode)
        self.paprika_mode = mode
