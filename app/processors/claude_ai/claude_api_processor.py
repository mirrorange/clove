from app.core.http_client import (
    Response,
    AsyncSession,
    create_session,
)
from datetime import datetime, timedelta, UTC
from typing import Dict, Optional
from loguru import logger
from fastapi.responses import StreamingResponse

from app.models.claude import MessagesAPIRequest, TextContent
from app.processors.base import BaseProcessor
from app.processors.claude_ai import ClaudeAIContext
from app.services.account import account_manager
from app.services.cache import cache_service
from app.services.oauth import oauth_authenticator
from app.core.account import Account
from app.core.exceptions import (
    ClaudeHttpError,
    ClaudeRateLimitedError,
    InvalidModelNameError,
    NoAccountsAvailableError,
    OAuthAuthenticationNotAllowedError,
)
from app.core.config import settings


class ClaudeAPIProcessor(BaseProcessor):
    """Processor that calls Claude Messages API directly using OAuth authentication."""

    def __init__(self):
        self.messages_api_url = (
            settings.claude_api_baseurl.encoded_string().rstrip("/") + "/v1/messages"
        )

    async def _request_messages_api(
        self, session: AsyncSession, request_json: str, headers: Dict[str, str]
    ) -> Response:
        """Make HTTP request with retry mechanism for curl_cffi exceptions."""
        response: Response = await session.request(
            "POST",
            self.messages_api_url,
            data=request_json,
            headers=headers,
            stream=True,
        )
        return response

    async def process(self, context: ClaudeAIContext) -> ClaudeAIContext:
        """
        Process Claude API request using OAuth authentication.

        Requires:
            - messages_api_request in context

        Produces:
            - response in context (StreamingResponse)
        """
        if context.response:
            logger.debug("Skipping ClaudeAPIProcessor due to existing response")
            return context

        if not context.messages_api_request:
            logger.warning(
                "Skipping ClaudeAPIProcessor due to missing messages_api_request"
            )
            return context

        self._insert_system_message(context)

        try:
            # First try to get account from cache service
            cached_account_id, checkpoints = cache_service.process_messages(
                context.messages_api_request.model,
                context.messages_api_request.messages,
                context.messages_api_request.system,
            )

            account = None
            if cached_account_id:
                account = await account_manager.get_account_by_id(cached_account_id)
                if account:
                    logger.info(f"Using cached account: {cached_account_id[:8]}...")

            # If no cached account or account not available, get a new one
            if not account:
                account = await account_manager.get_account_for_oauth(
                    is_max=True
                    if (context.messages_api_request.model in settings.max_models)
                    else None
                )

            with account:
                request_json = context.messages_api_request.model_dump_json(
                    exclude_none=True
                )

                # Try the request, with one retry on 401 authentication error
                response, session = await self._execute_api_request_with_retry(
                    account, request_json, context
                )

                resets_at = response.headers.get("anthropic-ratelimit-unified-reset")
                if resets_at:
                    try:
                        resets_at = int(resets_at)
                        account.resets_at = datetime.fromtimestamp(resets_at, tz=UTC)
                    except ValueError:
                        logger.error(
                            f"Invalid resets_at format from Claude API: {resets_at}"
                        )
                        account.resets_at = None

                async def stream_response():
                    async for chunk in response.aiter_bytes():
                        yield chunk

                    await session.close()

                filtered_headers = {}
                for key, value in response.headers.items():
                    if key.lower() in ["content-encoding", "content-length"]:
                        logger.debug(f"Filtering out header: {key}: {value}")
                        continue
                    filtered_headers[key] = value

                context.response = StreamingResponse(
                    stream_response(),
                    status_code=response.status_code,
                    headers=filtered_headers,
                )

                # Stop pipeline on success
                context.metadata["stop_pipeline"] = True
                logger.info("Successfully processed request via Claude API")

                # Store checkpoints in cache service after successful request
                if checkpoints and account:
                    cache_service.add_checkpoints(
                        checkpoints, account.organization_uuid
                    )

        except (NoAccountsAvailableError, InvalidModelNameError):
            logger.debug("No accounts available for Claude API, continuing pipeline")

        return context

    async def _execute_api_request_with_retry(
        self,
        account: Account,
        request_json: str,
        context: ClaudeAIContext,
    ) -> tuple[Response, AsyncSession]:
        """
        Execute API request with retry on 401 authentication error.
        
        If a 401 error occurs with "Invalid authentication credentials",
        try to re-authenticate using the cookie and retry once.
        """
        retried = False

        while True:
            headers = self._prepare_headers(
                account.oauth_token.access_token,
                context.messages_api_request,
                context.original_request,
            )

            session = create_session(
                proxy=settings.proxy_url,
                timeout=settings.request_timeout,
                impersonate="chrome",
                follow_redirects=False,
            )

            response = await self._request_messages_api(session, request_json, headers)

            # Handle rate limiting
            if response.status_code == 429:
                await session.close()
                next_hour = datetime.now(UTC).replace(
                    minute=0, second=0, microsecond=0
                ) + timedelta(hours=1)
                resets_at = response.headers.get("anthropic-ratelimit-unified-reset")
                if resets_at:
                    try:
                        resets_at_dt = datetime.fromtimestamp(int(resets_at), tz=UTC)
                    except ValueError:
                        resets_at_dt = next_hour
                else:
                    resets_at_dt = next_hour
                raise ClaudeRateLimitedError(resets_at=resets_at_dt)

            if response.status_code >= 400:
                error_data = await response.json()
                await session.close()

                if (
                    response.status_code == 400
                    and error_data.get("error", {}).get("message")
                    == "system: Invalid model name"
                ):
                    raise InvalidModelNameError(context.messages_api_request.model)

                if (
                    response.status_code == 401
                    and error_data.get("error", {}).get("message")
                    == "OAuth authentication is currently not allowed for this organization."
                ):
                    raise OAuthAuthenticationNotAllowedError()

                # Handle 401 authentication_error - try re-auth with cookie
                if (
                    response.status_code == 401
                    and error_data.get("error", {}).get("type") == "authentication_error"
                    and not retried
                    and account.cookie_value
                ):
                    logger.warning(
                        f"401 authentication error for account {account.organization_uuid[:8]}..., "
                        "attempting re-authentication with cookie"
                    )
                    
                    success = await self._try_reauthenticate_account(account)
                    if success:
                        logger.info(
                            f"Re-authentication successful for account {account.organization_uuid[:8]}..., retrying request"
                        )
                        retried = True
                        continue
                    else:
                        logger.error(
                            f"Re-authentication failed for account {account.organization_uuid[:8]}..."
                        )

                logger.error(
                    f"Claude API error: {response.status_code} - {error_data}"
                )
                raise ClaudeHttpError(
                    url=self.messages_api_url,
                    status_code=response.status_code,
                    error_type=error_data.get("error", {}).get("type", "unknown"),
                    error_message=error_data.get("error", {}).get(
                        "message", "Unknown error"
                    ),
                )

            # Success
            return response, session

    async def _try_reauthenticate_account(self, account: Account) -> bool:
        """
        Try to re-authenticate an account using its cookie.
        Returns True if successful, False otherwise.
        """
        try:
            success = await oauth_authenticator.authenticate_account(account)
            return success
        except Exception as e:
            logger.error(f"Re-authentication error: {e}")
            return False

    def _insert_system_message(self, context: ClaudeAIContext) -> None:
        """Insert system message into the request."""

        request = context.messages_api_request

        # Handle system field
        system_message_text = (
            "You are Claude Code, Anthropic's official CLI for Claude."
        )
        system_message = TextContent(type="text", text=system_message_text)

        if isinstance(request.system, str) and request.system:
            request.system = [
                system_message,
                TextContent(type="text", text=request.system),
            ]
        elif isinstance(request.system, list) and request.system:
            if request.system[0].text == system_message_text:
                logger.debug("System message already exists, skipping injection.")
            else:
                request.system = [system_message] + request.system
        else:
            request.system = [system_message]

    def _prepare_headers(
        self,
        access_token: str,
        request: MessagesAPIRequest,
        original_request=None,
    ) -> Dict[str, str]:
        """Prepare headers for Claude API request.

        Beta headers: oauth 是 OAuth 认证必需的。
        effort 和 structured-outputs 已 GA，不再需要 beta header。
        客户端的 anthropic-beta header 会被透传（去重合并）。
        """
        # oauth beta 是 OAuth 认证必需的
        beta_features = ["oauth-2025-04-20"]

        # 透传客户端 anthropic-beta header，与内部 beta 去重合并
        if original_request:
            client_beta = original_request.headers.get("anthropic-beta", "")
            if client_beta:
                for beta in client_beta.split(","):
                    beta = beta.strip()
                    if beta and beta not in beta_features:
                        beta_features.append(beta)

        return {
            "Authorization": f"Bearer {access_token}",
            "anthropic-beta": ",".join(beta_features),
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
