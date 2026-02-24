import asyncio
from typing import Dict, Optional
from datetime import datetime, timedelta
import threading
from loguru import logger

from app.core.config import settings


class ToolCallState:
    """State for a pending tool call."""

    def __init__(self, tool_use_id: str, session_id: str):
        self.tool_use_id = tool_use_id
        self.session_id = session_id
        self.created_at = datetime.now()
        self.message_id: Optional[str] = None


class ToolCallManager:
    """
    Singleton manager for tool call states.
    """

    _instance: Optional["ToolCallManager"] = None
    _lock = threading.Lock()

    def __new__(cls):
        """Implement singleton pattern."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the ToolCallManager."""
        self._tool_calls: Dict[str, ToolCallState] = {}
        self._cleanup_task: Optional[asyncio.Task] = None
        self._tool_call_timeout = settings.tool_call_timeout
        self._cleanup_interval = settings.tool_call_cleanup_interval

        logger.info(
            f"ToolCallManager initialized with timeout={self._tool_call_timeout}s, "
            f"cleanup_interval={self._cleanup_interval}s"
        )

    def register_tool_call(
        self, tool_use_id: str, session_id: str, message_id: Optional[str] = None
    ) -> None:
        """
        Register a new tool call.

        Args:
            tool_use_id: Unique identifier for the tool use
            session_id: Session ID associated with this tool call
            message_id: Optional message ID for tracking
        """
        tool_call_state = ToolCallState(tool_use_id, session_id)
        tool_call_state.message_id = message_id

        self._tool_calls[tool_use_id] = tool_call_state

        logger.info(f"Registered tool call: {tool_use_id} for session: {session_id}")

    def get_tool_call(self, tool_use_id: str) -> Optional[ToolCallState]:
        """
        Get a tool call state by ID.

        Args:
            tool_use_id: Tool use ID to lookup

        Returns:
            ToolCallState if found, None otherwise
        """
        return self._tool_calls.get(tool_use_id)

    def complete_tool_call(self, tool_use_id: str) -> None:
        """
        Mark a tool call as completed and return the associated session ID.

        Args:
            tool_use_id: Tool use ID to complete
        """
        tool_call = self._tool_calls.get(tool_use_id)
        if tool_call:
            del self._tool_calls[tool_use_id]

        logger.info(f"Completed tool call: {tool_use_id}")

    async def start_cleanup_task(self) -> None:
        """Start the background task for cleaning up expired tool calls."""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info("Started tool call cleanup task")

    async def stop_cleanup_task(self) -> None:
        """Stop the background cleanup task."""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            logger.info("Stopped tool call cleanup task")

    async def _cleanup_loop(self) -> None:
        """Background loop to clean up expired tool calls."""
        while True:
            try:
                self._cleanup_expired_tool_calls()
                await asyncio.sleep(self._cleanup_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in tool call cleanup loop: {e}")
                await asyncio.sleep(self._cleanup_interval)

    def _cleanup_expired_tool_calls(self) -> None:
        """Clean up all expired tool calls."""
        current_time = datetime.now()
        timeout_duration = timedelta(seconds=self._tool_call_timeout)
        expired_tool_calls = []

        for tool_use_id, tool_call in self._tool_calls.items():
            if (current_time - tool_call.created_at) > timeout_duration:
                expired_tool_calls.append(tool_use_id)

        for tool_use_id in expired_tool_calls:
            tool_call = self._tool_calls[tool_use_id]
            del self._tool_calls[tool_use_id]

        if expired_tool_calls:
            logger.info(f"Cleaned up {len(expired_tool_calls)} expired tool calls")

    async def cleanup_all(self) -> None:
        """Clean up all tool calls and stop the cleanup task."""
        await self.stop_cleanup_task()
        self._tool_calls.clear()
        logger.info("Cleaned up all tool calls")

    def __repr__(self) -> str:
        """String representation of the ToolCallManager."""
        return f"<ToolCallManager tool_calls={len(self._tool_calls)}>"


tool_call_manager = ToolCallManager()
