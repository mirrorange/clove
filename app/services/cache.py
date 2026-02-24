import asyncio
import hashlib
import json
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from loguru import logger

from app.core.config import settings
from app.models.claude import (
    Base64ImageSource,
    FileImageSource,
    ImageContent,
    InputMessage,
    ContentBlock,
    ServerToolUseContent,
    TextContent,
    ThinkingContent,
    ToolResultContent,
    ToolUseContent,
    URLImageSource,
    WebSearchToolResultContent,
)


class CacheCheckpoint:
    """Cache checkpoint with timestamp."""

    def __init__(self, checkpoint: str, account_id: str):
        self.checkpoint = checkpoint
        self.account_id = account_id
        self.created_at = datetime.now()


class CacheService:
    """
    Service for managing prompt cache mapping to accounts.
    Ensures requests with cached prompts are sent to the same account.
    """

    _instance: Optional["CacheService"] = None
    _lock = threading.Lock()

    def __new__(cls):
        """Implement singleton pattern."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the CacheService."""
        # Maps checkpoint hash -> CacheCheckpoint
        self._checkpoints: Dict[str, CacheCheckpoint] = {}
        self._cleanup_task: Optional[asyncio.Task] = None

        logger.info(
            f"CacheService initialized with timeout={settings.cache_timeout}s, "
            f"cleanup_interval={settings.cache_cleanup_interval}s"
        )

    def process_messages(
        self,
        model: str,
        messages: List[InputMessage],
        system: Optional[List[TextContent]] = None,
    ) -> Tuple[Optional[str], List[str]]:
        """
        Process messages to find cached account and extract new checkpoints.

        Args:
            messages: List of input messages
            system: Optional system messages

        Returns:
            Tuple of (account_id, checkpoints) where:
            - account_id: The account ID if a cached prompt was found, None otherwise
            - checkpoints: List of feature values for content blocks with cache_control
        """
        account_id: Optional[str] = None
        checkpoints: List[str] = []

        hasher = hashlib.sha256()

        self._update_hasher(hasher, {"model": model})

        if system:
            for text_content in system:
                content_block_data = self._content_block_to_dict(text_content)
                self._update_hasher(hasher, content_block_data)

                feature_value = hasher.hexdigest()

                if text_content.cache_control:
                    checkpoints.append(feature_value)

                if feature_value in self._checkpoints:
                    account_id = self._checkpoints[feature_value].account_id

        for message in messages:
            self._update_hasher(hasher, {"role": message.role.value})

            if isinstance(message.content, str):
                self._update_hasher(hasher, {"type": "text", "text": message.content})
            elif isinstance(message.content, list):
                for content_block in message.content:
                    content_block_data = self._content_block_to_dict(content_block)
                    self._update_hasher(hasher, content_block_data)

                    feature_value = hasher.hexdigest()

                    if (
                        hasattr(content_block, "cache_control")
                        and content_block.cache_control
                    ):
                        checkpoints.append(feature_value)

                    if feature_value in self._checkpoints:
                        account_id = self._checkpoints[feature_value].account_id

        if account_id:
            logger.debug(
                f"Cache hit: account_id={account_id}, feature={feature_value[:16]}..."
            )

        return account_id, checkpoints

    def add_checkpoints(self, checkpoints: List[str], account_id: str) -> None:
        """
        Add checkpoint mappings to the cache.

        Args:
            checkpoints: List of feature values to map
            account_id: Account ID to map to
        """
        for checkpoint in checkpoints:
            self._checkpoints[checkpoint] = CacheCheckpoint(checkpoint, account_id)
            logger.debug(
                f"Added checkpoint mapping: {checkpoint[:16]}... -> {account_id}"
            )

        logger.debug(
            f"Cache updated: {len(checkpoints)} checkpoints added. "
            f"Total cache size: {len(self._checkpoints)}"
        )

    def _update_hasher(self, hasher: "hashlib._Hash", data: Dict) -> None:
        """
        Update the hasher with new data in a consistent way.

        Args:
            hasher: The hash object to update
            data: Dictionary data to add to the hash
        """
        # Serialize data in a consistent way
        json_str = json.dumps(data, sort_keys=True, separators=(",", ":"))

        # Add a delimiter to ensure proper separation between blocks
        hasher.update(b"\x00")  # NULL byte as delimiter
        hasher.update(json_str.encode("utf-8"))

    def _content_block_to_dict(self, content_block: ContentBlock) -> Dict:
        """
        Convert a ContentBlock to a dictionary for hashing.
        Only includes relevant fields for cache matching.
        """
        result = {"type": content_block.type}

        if isinstance(content_block, TextContent):
            result["text"] = content_block.text
        elif isinstance(content_block, ThinkingContent):
            result["thinking"] = content_block.thinking
        elif isinstance(content_block, ToolUseContent) or isinstance(
            content_block, ServerToolUseContent
        ):
            result["id"] = content_block.id
        elif isinstance(content_block, ToolResultContent) or isinstance(
            content_block, WebSearchToolResultContent
        ):
            result["tool_use_id"] = content_block.tool_use_id
        elif isinstance(content_block, ImageContent):
            result["source_type"] = content_block.source.type
            if isinstance(content_block.source, Base64ImageSource):
                result["source_data"] = content_block.source.data
            elif isinstance(content_block.source, URLImageSource):
                result["source_url"] = content_block.source.url
            elif isinstance(content_block.source, FileImageSource):
                result["source_file"] = content_block.source.file_uuid

        return result

    async def start_cleanup_task(self) -> None:
        """Start the background task for cleaning up expired cache checkpoints."""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info("Started cache cleanup task")

    async def stop_cleanup_task(self) -> None:
        """Stop the background cleanup task."""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            logger.info("Stopped cache cleanup task")

    async def _cleanup_loop(self) -> None:
        """Background loop to clean up expired cache checkpoints."""
        while True:
            try:
                self._cleanup_expired_checkpoints()
                await asyncio.sleep(settings.cache_cleanup_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cache cleanup loop: {e}")
                await asyncio.sleep(settings.cache_cleanup_interval)

    def _cleanup_expired_checkpoints(self) -> None:
        """Clean up all expired cache checkpoints."""
        current_time = datetime.now()
        timeout_duration = timedelta(seconds=settings.cache_timeout)
        expired_checkpoints = []

        for checkpoint_hash, cache_checkpoint in self._checkpoints.items():
            if (current_time - cache_checkpoint.created_at) > timeout_duration:
                expired_checkpoints.append(checkpoint_hash)

        for checkpoint_hash in expired_checkpoints:
            del self._checkpoints[checkpoint_hash]

        if expired_checkpoints:
            logger.info(
                f"Cleaned up {len(expired_checkpoints)} expired cache checkpoints"
            )

    async def cleanup_all(self) -> None:
        """Clean up all cache checkpoints and stop the cleanup task."""
        await self.stop_cleanup_task()
        self._checkpoints.clear()
        logger.info("Cleaned up all cache checkpoints")

    def __repr__(self) -> str:
        """String representation of the CacheService."""
        return f"<CacheService checkpoints={len(self._checkpoints)}>"


cache_service = CacheService()
