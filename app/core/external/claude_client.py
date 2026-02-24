import json
from loguru import logger
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from urllib.parse import urljoin
from uuid import uuid4

from app.core.http_client import (
    create_session,
    Response,
    AsyncSession,
)

from app.core.config import settings
from app.core.exceptions import (
    ClaudeAuthenticationError,
    ClaudeRateLimitedError,
    CloudflareBlockedError,
    OrganizationDisabledError,
    ClaudeHttpError,
)
from app.models.internal import UploadResponse
from app.core.account import Account


class ClaudeWebClient:
    """Client for interacting with Claude.ai."""

    def __init__(self, account: Account):
        self.account = account
        self.session: Optional[AsyncSession] = None
        self.endpoint = settings.claude_ai_url.encoded_string().rstrip("/")

    async def initialize(self):
        """Initialize the client session."""
        self.session = create_session(
            timeout=settings.request_timeout,
            impersonate="chrome",
            proxy=settings.proxy_url,
            follow_redirects=False,
        )

    async def cleanup(self):
        """Clean up resources."""
        if self.session:
            await self.session.close()

    def _build_headers(
        self, cookie: str, conv_uuid: Optional[str] = None
    ) -> Dict[str, str]:
        """Build request headers."""
        headers = {
            "Accept": "text/event-stream",
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "no-cache",
            "Cookie": cookie,
            "Origin": self.endpoint,
            "Referer": f"{self.endpoint}/new",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }

        if conv_uuid:
            headers["Referer"] = f"{self.endpoint}/chat/{conv_uuid}"

        return headers

    async def _request(
        self,
        method: str,
        url: str,
        conv_uuid: Optional[str] = None,
        stream=None,
        **kwargs,
    ) -> Response:
        """Make HTTP request with error handling."""
        if not self.session:
            await self.initialize()

        with self.account as account:
            cookie_value = account.cookie_value
            headers = self._build_headers(cookie_value, conv_uuid)
            kwargs["headers"] = {**headers, **kwargs.get("headers", {})}
            response: Response = await self.session.request(
                method=method, url=url, stream=stream, **kwargs
            )

            if response.status_code < 300:
                return response

            if response.status_code == 302:
                raise CloudflareBlockedError()

            try:
                error_data = await response.json()
                error_body = error_data.get("error", {})
                error_message = error_body.get("message", "Unknown error")
                error_type = error_body.get("type", "unknown")
            except Exception:
                error_message = f"HTTP {response.status_code} error with empty response"
                error_type = "empty_response"

            if (
                response.status_code == 400
                and error_message == "This organization has been disabled."
            ):
                raise OrganizationDisabledError()

            if response.status_code == 403 and error_message == "Invalid authorization":
                raise ClaudeAuthenticationError()

            if response.status_code == 429:
                try:
                    error_message_data = json.loads(error_message)
                    resets_at = error_message_data.get("resetsAt")
                    if resets_at and isinstance(resets_at, int):
                        reset_time = datetime.fromtimestamp(resets_at, tz=timezone.utc)
                        logger.error(f"Rate limit exceeded, resets at: {reset_time}")
                        raise ClaudeRateLimitedError(resets_at=reset_time)
                except json.JSONDecodeError:
                    pass

            raise ClaudeHttpError(
                url=url,
                status_code=response.status_code,
                error_type=error_type,
                error_message=error_message,
            )

    async def create_conversation(self) -> str:
        """Create a new conversation."""
        url = urljoin(
            self.endpoint,
            f"/api/organizations/{self.account.organization_uuid}/chat_conversations",
        )

        uuid = uuid4()

        payload = {
            "name": "Hello World!",
            "uuid": str(uuid),
        }
        response = await self._request("POST", url, json=payload)

        data = await response.json()
        conv_uuid = data.get("uuid")
        paprika_mode = data.get("settings", {}).get("paprika_mode")
        logger.info(f"Created conversation: {conv_uuid}")

        return conv_uuid, paprika_mode

    async def set_paprika_mode(self, conv_uuid: str, mode: Optional[str]) -> None:
        """Set the conversation mode."""
        url = urljoin(
            self.endpoint,
            f"/api/organizations/{self.account.organization_uuid}/chat_conversations/{conv_uuid}",
        )
        payload = {"settings": {"paprika_mode": mode}}
        await self._request("PUT", url, json=payload)
        logger.debug(f"Set conversation {conv_uuid} mode: {mode}")

    async def upload_file(
        self, file_data: bytes, filename: str, content_type: str
    ) -> str:
        """Upload a file and return file UUID."""
        url = urljoin(self.endpoint, f"/api/{self.account.organization_uuid}/upload")
        files = {"file": (filename, file_data, content_type)}

        response = await self._request("POST", url, files=files)

        data = UploadResponse.model_validate(await response.json())
        return data.file_uuid

    async def send_message(self, payload: Dict[str, Any], conv_uuid: str) -> Response:
        """Send a message and return the response."""
        url = urljoin(
            self.endpoint,
            f"/api/organizations/{self.account.organization_uuid}/chat_conversations/{conv_uuid}/completion",
        )

        headers = {
            "Accept": "text/event-stream",
        }

        response = await self._request(
            "POST", url, conv_uuid=conv_uuid, json=payload, headers=headers, stream=True
        )

        return response

    async def send_tool_result(self, payload: Dict[str, Any], conv_uuid: str):
        """Send tool result to Claude.ai."""
        url = urljoin(
            self.endpoint,
            f"/api/organizations/{self.account.organization_uuid}/chat_conversations/{conv_uuid}/tool_result",
        )

        await self._request("POST", url, conv_uuid=conv_uuid, json=payload)

    async def delete_conversation(self, conv_uuid: str) -> None:
        """Delete a conversation."""
        if not conv_uuid:
            return

        url = urljoin(
            self.endpoint,
            f"/api/organizations/{self.account.organization_uuid}/chat_conversations/{conv_uuid}",
        )
        try:
            await self._request("DELETE", url, conv_uuid=conv_uuid)
            logger.info(f"Deleted conversation: {conv_uuid}")
        except Exception as e:
            logger.warning(f"Failed to delete conversation: {e}")
