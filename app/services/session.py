import asyncio
from typing import Dict, Optional
from datetime import datetime, timedelta
import threading
from loguru import logger

from app.core.config import settings
from app.core.claude_session import ClaudeWebSession


class SessionManager:
    """
    Singleton manager for Claude sessions with automatic cleanup.
    """

    _instance: Optional["SessionManager"] = None
    _lock = threading.Lock()

    def __new__(cls):
        """Implement singleton pattern."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the SessionManager."""
        self._sessions: Dict[str, ClaudeWebSession] = {}
        self._session_lock = asyncio.Lock()
        self._cleanup_task: Optional[asyncio.Task] = None
        self._session_timeout = settings.session_timeout
        self._cleanup_interval = settings.session_cleanup_interval

        logger.info(
            f"SessionManager initialized with timeout={self._session_timeout}s, "
            f"cleanup_interval={self._cleanup_interval}s"
        )

    async def get_or_create_session(self, session_id: str) -> ClaudeWebSession:
        """
        Get or create a new Claude session.

        Args:
            session_id: Unique identifier for the session

        Returns:
            Created ClaudeSession instance
        """
        async with self._session_lock:
            if session_id in self._sessions:
                return self._sessions[session_id]

            session = ClaudeWebSession(session_id)
            await session.initialize()
            self._sessions[session_id] = session

            logger.debug(f"Created new session: {session_id}")
            return session

    async def get_session(self, session_id: str) -> Optional[ClaudeWebSession]:
        """
        Get a session by ID.

        Args:
            session_id: Unique identifier for the session

        Returns:
            ClaudeSession instance if found, None otherwise
        """
        async with self._session_lock:
            session = self._sessions.get(session_id)

            if session:
                # Check if session is expired
                if await self._is_session_expired(session):
                    logger.debug(f"Session {session_id} is expired, removing")
                    await self._remove_session(session_id)
                    return None

            return session

    async def remove_session(self, session_id: str) -> None:
        """
        Remove a session by ID.

        Args:
            session_id: Unique identifier for the session
        """
        async with self._session_lock:
            if session_id in self._sessions:
                await self._remove_session(session_id)

    async def _is_session_expired(self, session: ClaudeWebSession) -> bool:
        """
        Check if a session is expired.

        A session is considered expired if its last_activity is older than session_timeout.

        Args:
            session: Session to check

        Returns:
            True if session is expired, False otherwise
        """
        current_time = datetime.now()
        timeout_duration = timedelta(seconds=self._session_timeout)

        return (current_time - session.last_activity) > timeout_duration

    async def _remove_session(self, session_id: str) -> None:
        """
        Remove a session and cleanup its resources.

        Note: This method should be called while holding the session lock.

        Args:
            session_id: ID of the session to remove
        """
        if session_id in self._sessions:
            session = self._sessions[session_id]
            asyncio.create_task(session.cleanup())  # Cleanup session asynchronously

            # Remove from sessions dict (should already have the lock)
            if session_id in self._sessions:
                del self._sessions[session_id]
            logger.debug(f"Removed session: {session_id}")

    async def start_cleanup_task(self) -> None:
        """Start the background task for cleaning up expired sessions."""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info("Started session cleanup task")

    async def stop_cleanup_task(self) -> None:
        """Stop the background cleanup task."""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            logger.info("Stopped session cleanup task")

    async def _cleanup_loop(self) -> None:
        """Background loop to clean up expired sessions."""
        while True:
            try:
                await self._cleanup_expired_sessions()
                await asyncio.sleep(self._cleanup_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(self._cleanup_interval)

    async def _cleanup_expired_sessions(self) -> None:
        """Clean up all expired sessions."""
        async with self._session_lock:
            expired_sessions = []

            for session_id, session in self._sessions.items():
                if await self._is_session_expired(session):
                    expired_sessions.append(session_id)

            for session_id in expired_sessions:
                await self._remove_session(session_id)

            if expired_sessions:
                logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")

    async def cleanup_all(self) -> None:
        """Clean up all sessions and stop the cleanup task."""
        await self.stop_cleanup_task()

        async with self._session_lock:
            session_ids = list(self._sessions.keys())

            for session_id in session_ids:
                await self._remove_session(session_id)

        logger.info("Cleaned up all sessions")

    def __repr__(self) -> str:
        """String representation of the SessionManager."""
        return f"<SessionManager sessions={len(self._sessions)}>"


session_manager = SessionManager()
