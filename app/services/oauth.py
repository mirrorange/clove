import base64
import hashlib
import secrets
import time
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse, parse_qs

from app.core.http_client import Response, create_session
from loguru import logger

from app.core.config import settings
from app.core.account import Account, AuthType, OAuthToken
from app.core.exceptions import (
    AppError,
    ClaudeAuthenticationError,
    ClaudeHttpError,
    CloudflareBlockedError,
    CookieAuthorizationError,
    OAuthExchangeError,
    OrganizationInfoError,
)


class OAuthAuthenticator:
    """OAuth authenticator for Claude accounts using cookies."""

    def _generate_pkce(self) -> Tuple[str, str]:
        """Generate PKCE verifier and challenge."""
        verifier = (
            base64.urlsafe_b64encode(secrets.token_bytes(32))
            .decode("utf-8")
            .rstrip("=")
        )
        challenge = (
            base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("utf-8")).digest())
            .decode("utf-8")
            .rstrip("=")
        )
        return verifier, challenge

    def _build_headers(self, cookie: str) -> Dict[str, str]:
        """Build request headers."""
        claude_endpoint = settings.claude_ai_url.encoded_string().rstrip("/")

        return {
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "no-cache",
            "Cookie": cookie,
            "Origin": claude_endpoint,
            "Referer": f"{claude_endpoint}/new",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }

    async def _request(self, method: str, url: str, **kwargs) -> Response:
        session = create_session(
            timeout=settings.request_timeout,
            impersonate="chrome",
            proxy=settings.proxy_url,
            follow_redirects=False,
        )
        async with session:
            response: Response = await session.request(method=method, url=url, **kwargs)

        if response.status_code == 302:
            raise CloudflareBlockedError()

        if response.status_code == 403:
            raise ClaudeAuthenticationError()

        if response.status_code >= 300:
            raise ClaudeHttpError(
                url=url,
                status_code=response.status_code,
                error_type="Unknown",
                error_message="Error occurred during request to Claude.ai",
            )

        return response

    async def get_organization_info(self, cookie: str) -> Tuple[str, List[str]]:
        """Get organization UUID and capabilities."""
        url = f"{settings.claude_ai_url.encoded_string().rstrip('/')}/api/organizations"
        headers = self._build_headers(cookie)

        try:
            response = await self._request("GET", url, headers=headers)

            org_data = await response.json()
            if org_data and isinstance(org_data, list):
                organization_uuid = None
                max_capabilities = []

                for org in org_data:
                    if "uuid" in org and "capabilities" in org:
                        capabilities = org.get("capabilities", [])

                        if "chat" not in capabilities:
                            continue

                        if len(capabilities) > len(max_capabilities):
                            organization_uuid = org.get("uuid")
                            max_capabilities = capabilities

                if organization_uuid:
                    logger.info(
                        f"Found organization UUID: {organization_uuid}, capabilities: {max_capabilities}"
                    )
                    return organization_uuid, max_capabilities

                raise OrganizationInfoError(
                    reason="No valid organization found with chat capabilities"
                )

            else:
                logger.error("No organization data found in response")
                raise OrganizationInfoError(reason="No organization data found")

        except AppError as e:
            raise e

        except Exception as e:
            logger.error(f"Error getting organization UUID: {e}")
            raise OrganizationInfoError(reason=str(e))

    async def authorize_with_cookie(
        self, cookie: str, organization_uuid: str
    ) -> Tuple[str, str]:
        """
        Use Cookie to automatically get authorization code.
        Returns: (authorization code, verifier)
        """
        verifier, challenge = self._generate_pkce()
        state = (
            base64.urlsafe_b64encode(secrets.token_bytes(32))
            .decode("utf-8")
            .rstrip("=")
        )

        authorize_url = settings.oauth_authorize_url.format(
            organization_uuid=organization_uuid
        )

        payload = {
            "response_type": "code",
            "client_id": settings.oauth_client_id,
            "organization_uuid": organization_uuid,
            "redirect_uri": settings.oauth_redirect_uri,
            "scope": "user:profile user:inference",
            "state": state,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }

        headers = self._build_headers(cookie)
        headers["Content-Type"] = "application/json"

        logger.debug(f"Requesting authorization from: {authorize_url}")

        response = await self._request(
            "POST", authorize_url, json=payload, headers=headers
        )

        auth_response = await response.json()
        redirect_uri = auth_response.get("redirect_uri")

        if not redirect_uri:
            logger.error("No redirect_uri in authorization response")
            raise CookieAuthorizationError(reason="No redirect URI found in response")

        logger.info(f"Got redirect URI: {redirect_uri}")

        parsed_url = urlparse(redirect_uri)
        query_params = parse_qs(parsed_url.query)

        if "code" not in query_params:
            logger.error("No authorization code in redirect_uri")
            raise CookieAuthorizationError(
                reason="No authorization code found in response"
            )

        auth_code = query_params["code"][0]
        response_state = query_params.get("state", [None])[0]

        logger.info(f"Extracted authorization code: {auth_code[:20]}...")

        if response_state:
            full_code = f"{auth_code}#{response_state}"
        else:
            full_code = auth_code

        return full_code, verifier

    async def exchange_token(self, code: str, verifier: str) -> Dict:
        """Exchange authorization code for access token."""
        parts = code.split("#")
        auth_code = parts[0]
        state = parts[1] if len(parts) > 1 else None

        data = {
            "code": auth_code,
            "grant_type": "authorization_code",
            "client_id": settings.oauth_client_id,
            "redirect_uri": settings.oauth_redirect_uri,
            "code_verifier": verifier,
        }

        if state:
            data["state"] = state

        try:
            response = await self._request(
                "POST",
                settings.oauth_token_url,
                json=data,
                headers={"Content-Type": "application/json"},
            )

            token_data = await response.json()

            if (
                "access_token" not in token_data
                or "refresh_token" not in token_data
                or "expires_in" not in token_data
            ):
                logger.error("Invalid token response received")
                raise OAuthExchangeError(reason="Invalid token response")

            return token_data

        except AppError as e:
            raise e

        except Exception as e:
            logger.error(f"Error exchanging token: {e}")
            raise OAuthExchangeError(reason=str(e))

    async def refresh_access_token(self, refresh_token: str) -> Optional[Dict]:
        """Refresh access token."""
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": settings.oauth_client_id,
        }

        try:
            response = await self._request(
                "POST",
                settings.oauth_token_url,
                json=data,
                headers={"Content-Type": "application/json"},
            )

            if response.status_code != 200:
                logger.error(f"Token refresh failed: {response.status_code}")
                return None

            token_data = await response.json()
            return token_data

        except Exception as e:
            logger.error(f"Error refreshing token: {e}")
            return None

    async def authenticate_account(self, account: Account) -> bool:
        """
        Authenticate an account using OAuth.
        Returns True if successful, False otherwise.
        """
        if not account.cookie_value:
            logger.error("Account has no cookie value")
            return False

        try:
            # Get organization UUID
            org_uuid, _ = await self.get_organization_info(account.cookie_value)

            # Get authorization code
            auth_result = await self.authorize_with_cookie(
                account.cookie_value, org_uuid
            )

            auth_code, verifier = auth_result

            # Exchange for tokens
            token_data = await self.exchange_token(auth_code, verifier)

            # Update account with OAuth tokens
            account.oauth_token = OAuthToken(
                access_token=token_data["access_token"],
                refresh_token=token_data["refresh_token"],
                expires_at=time.time() + token_data["expires_in"],
            )
            account.auth_type = AuthType.BOTH
            account.save()

            logger.info(
                f"Successfully authenticated account with OAuth: {account.organization_uuid[:8]}..."
            )
            return True

        except Exception as e:
            logger.error(f"OAuth authentication failed: {e}")
            return False

    async def refresh_account_token(self, account: Account) -> bool:
        """
        Refresh OAuth token for an account.
        Returns True if successful, False otherwise.
        """
        if not account.oauth_token or not account.oauth_token.refresh_token:
            logger.error("Account has no refresh token")
            return False

        token_data = await self.refresh_access_token(account.oauth_token.refresh_token)
        if not token_data:
            return False

        account.oauth_token = OAuthToken(
            access_token=token_data["access_token"],
            refresh_token=token_data["refresh_token"],
            expires_at=time.time() + token_data["expires_in"],
        )
        account.save()

        logger.info(
            f"Successfully refreshed OAuth token for account: {account.organization_uuid[:8]}..."
        )
        return True


oauth_authenticator = OAuthAuthenticator()
