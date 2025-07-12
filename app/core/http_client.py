"""HTTP client abstraction layer that supports both curl_cffi and httpx."""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Tuple, AsyncIterator
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_fixed,
)
from loguru import logger
import json

from app.core.config import settings
from app.utils.retry import log_before_sleep
from app.utils.proxy import parse_proxy_url, validate_proxy_url, get_curl_proxy_url, get_httpx_proxy_url

# Try to import curl_cffi, fall back to httpx if not available
try:
    from curl_cffi.requests import (
        AsyncSession as CurlAsyncSession,
        Response as CurlResponse,
    )
    from curl_cffi.requests.exceptions import RequestException as CurlRequestException
    import curl_cffi

    CURL_CFFI_AVAILABLE = True
except ImportError:
    CURL_CFFI_AVAILABLE = False

# Always try to import httpx as fallback
try:
    import httpx

    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

if not CURL_CFFI_AVAILABLE and not HTTPX_AVAILABLE:
    raise ImportError(
        "Neither curl_cffi nor httpx is installed. Please install at least one of them."
    )


class Response(ABC):
    """Abstract response class."""

    @property
    @abstractmethod
    def status_code(self) -> int:
        """Get response status code."""
        pass

    @abstractmethod
    def json(self) -> Any:
        """Parse response as JSON."""
        pass

    @abstractmethod
    async def ajson(self) -> Any:
        """Parse response as JSON asynchronously."""
        pass

    @property
    @abstractmethod
    def headers(self) -> Dict[str, str]:
        """Get response headers."""
        pass

    @abstractmethod
    def aiter_bytes(self, chunk_size: Optional[int] = None) -> AsyncIterator[bytes]:
        """Iterate over response bytes."""
        pass


class CurlResponseWrapper(Response):
    """curl_cffi response wrapper."""

    def __init__(self, response: "CurlResponse", stream: bool = False):
        self._response = response

    @property
    def status_code(self) -> int:
        return self._response.status_code

    def json(self) -> Any:
        return self._response.json()

    async def ajson(self) -> Any:
        content = ""
        async for chunk in self._response.aiter_content():
            content += chunk.decode("utf-8")
        return json.loads(content)

    @property
    def headers(self) -> Dict[str, str]:
        return self._response.headers

    async def aiter_bytes(
        self, chunk_size: Optional[int] = None
    ) -> AsyncIterator[bytes]:
        async for chunk in self._response.aiter_content(chunk_size):
            yield chunk
        await self._response.aclose()


class HttpxResponse(Response):
    """httpx response wrapper."""

    def __init__(self, response: httpx.Response):
        self._response = response

    @property
    def status_code(self) -> int:
        return self._response.status_code

    def json(self) -> Any:
        return self._response.json()

    async def ajson(self) -> Any:
        await self._response.aread()
        return self._response.json()

    @property
    def headers(self) -> Dict[str, str]:
        return self._response.headers

    async def aiter_bytes(
        self, chunk_size: Optional[int] = None
    ) -> AsyncIterator[bytes]:
        async for chunk in self._response.aiter_bytes(chunk_size):
            yield chunk
        await self._response.aclose()


class AsyncSession(ABC):
    """Abstract async session class."""

    @abstractmethod
    async def request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        json: Optional[Any] = None,
        data: Optional[Any] = None,
        stream: bool = False,
        **kwargs,
    ) -> Response:
        """Make an HTTP request."""
        pass

    @abstractmethod
    async def close(self):
        """Close the session."""
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


if CURL_CFFI_AVAILABLE:

    class CurlAsyncSessionWrapper(AsyncSession):
        """curl_cffi async session wrapper."""

        def __init__(
            self,
            timeout: int = settings.request_timeout,
            impersonate: str = "chrome",
            proxy: Optional[str] = settings.proxy_url,
            follow_redirects: bool = True,
        ):
            if not CURL_CFFI_AVAILABLE:
                raise ImportError("curl_cffi is not installed")

            # Parse and validate proxy URL
            if proxy:
                logger.info(f"[PROXY] Configuring proxy for curl_cffi: {proxy}")
                parsed_proxy = get_curl_proxy_url(proxy)
                is_valid, error_msg = validate_proxy_url(parsed_proxy)
                if not is_valid:
                    logger.error(f"Invalid proxy URL: {error_msg}")
                    raise ValueError(f"Invalid proxy URL: {error_msg}")
                proxy = parsed_proxy
                logger.info(f"[PROXY] Parsed proxy URL for curl_cffi: {proxy}")
            else:
                logger.info("[PROXY] No proxy configured for curl_cffi session")

            self._session = CurlAsyncSession(
                timeout=timeout,
                impersonate=impersonate,
                proxy=proxy,
                allow_redirects=follow_redirects,
            )

        def process_files(self, files: dict) -> curl_cffi.CurlMime:
            # Create multipart form
            multipart = curl_cffi.CurlMime()

            # Handle different file formats
            if isinstance(files, dict):
                for field_name, file_info in files.items():
                    if isinstance(file_info, tuple):
                        # Format: {"field": (filename, data, content_type)}
                        if len(file_info) >= 3:
                            filename, file_data, content_type = file_info[:3]
                        elif len(file_info) == 2:
                            filename, file_data = file_info
                            content_type = "application/octet-stream"
                        else:
                            raise ValueError(
                                f"Invalid file tuple format for field {field_name}"
                            )

                        multipart.addpart(
                            name=field_name,
                            content_type=content_type,
                            filename=filename,
                            data=file_data,
                        )
                    else:
                        # Simple format: {"field": data}
                        multipart.addpart(
                            name=field_name,
                            data=file_info,
                        )

            return multipart

        @retry(
            stop=stop_after_attempt(settings.request_retries),
            wait=wait_fixed(settings.request_retry_interval),
            retry=retry_if_exception_type(CurlRequestException),
            before_sleep=log_before_sleep,
            reraise=True,
        )
        async def request(
            self,
            method: str,
            url: str,
            headers: Optional[Dict[str, str]] = None,
            json: Optional[Any] = None,
            data: Optional[Any] = None,
            stream: bool = False,
            **kwargs,
        ) -> Response:
            logger.debug(f"Making {method} request to {url}")
            logger.debug(f"[PROXY] Request through curl_cffi using proxy: {self._session.proxy if hasattr(self._session, 'proxy') else 'No proxy'}")

            # Handle file uploads - convert files parameter to multipart
            files = kwargs.pop("files", None)

            multipart = None

            if files:
                multipart = self.process_files(files)
                kwargs["multipart"] = multipart

            try:
                response = await self._session.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=json,
                    data=data,
                    stream=stream,
                    **kwargs,
                )
                return CurlResponseWrapper(response)
            finally:
                if multipart:
                    multipart.close()

        async def close(self):
            await self._session.close()


if HTTPX_AVAILABLE:

    class HttpxAsyncSession(AsyncSession):
        """httpx async session wrapper."""

        def __init__(
            self,
            timeout: int = settings.request_timeout,
            impersonate: str = "chrome",
            proxy: Optional[str] = settings.proxy_url,
            follow_redirects: bool = True,
        ):
            if not HTTPX_AVAILABLE:
                raise ImportError("httpx is not installed")

            # Parse and validate proxy URL
            if proxy:
                logger.info(f"[PROXY] Configuring proxy for httpx: {proxy}")
                parsed_proxy = get_httpx_proxy_url(proxy)
                is_valid, error_msg = validate_proxy_url(parsed_proxy)
                if not is_valid:
                    logger.error(f"Invalid proxy URL: {error_msg}")
                    raise ValueError(f"Invalid proxy URL: {error_msg}")
                proxy = parsed_proxy
                logger.info(f"[PROXY] Parsed proxy URL for httpx: {proxy}")
                
                # Warn if SOCKS5 is used with httpx
                if proxy.startswith('socks5://'):
                    logger.warning("SOCKS5 proxy is not natively supported by httpx. Consider using curl_cffi or installing httpx-socks.")
            else:
                logger.info("[PROXY] No proxy configured for httpx session")

            # Create a custom SSL context that doesn't verify certificates
            # Note: This should only be used for development/testing with trusted proxies
            import ssl

            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

            self._client = httpx.AsyncClient(
                timeout=timeout,
                proxy=proxy,
                follow_redirects=follow_redirects,
                verify=ssl_context,  # Use custom SSL context
            )

        async def stream(
            self,
            method: str,
            url: str,
            headers: Optional[Dict[str, str]] = None,
            json: Optional[Any] = None,
            data: Optional[Any] = None,
            **kwargs,
        ) -> Response:
            """
            Alternative to `httpx.request()` that streams the response body
            instead of loading it into memory at once.

            **Parameters**: See `httpx.request`.

            See also: [Streaming Responses][0]

            [0]: /quickstart#streaming-responses
            """
            request = self._client.build_request(
                method=method,
                url=url,
                data=data,
                json=json,
                headers=headers,
                **kwargs,
            )
            response = await self._client.send(
                request=request,
                stream=True,
            )

            return response

        @retry(
            stop=stop_after_attempt(settings.request_retries),
            wait=wait_fixed(settings.request_retry_interval),
            retry=retry_if_exception_type(httpx.RequestError),
            before_sleep=log_before_sleep,
            reraise=True,
        )
        async def request(
            self,
            method: str,
            url: str,
            headers: Optional[Dict[str, str]] = None,
            json: Optional[Any] = None,
            data: Optional[Any] = None,
            stream: bool = False,
            **kwargs,
        ) -> Response:
            logger.debug(f"Making {method} request to {url}")
            logger.debug(f"[PROXY] Request through httpx using proxy: {self._client.proxy if hasattr(self._client, 'proxy') else 'No proxy'}")
            if stream:
                response = await self.stream(
                    method=method,
                    url=url,
                    headers=headers,
                    json=json,
                    data=data,
                    **kwargs,
                )
            else:
                response = await self._client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=json,
                    data=data,
                    **kwargs,
                )

            return HttpxResponse(response)

        async def close(self):
            await self._client.aclose()

def create_session(
    timeout: int = settings.request_timeout,
    impersonate: str = "chrome",
    proxy: Optional[str] = settings.proxy_url,
    follow_redirects: bool = True,
) -> AsyncSession:
    """Create an async session using the available HTTP client.

    Prefers curl_cffi if available, falls back to httpx.
    """
    if CURL_CFFI_AVAILABLE:
        logger.debug("Using curl_cffi as HTTP client")
        return CurlAsyncSessionWrapper(
            timeout=timeout,
            impersonate=impersonate,
            proxy=proxy,
            follow_redirects=follow_redirects,
        )
    else:
        logger.debug("Using httpx as HTTP client (curl_cffi not available)")
        return HttpxAsyncSession(
            timeout=timeout,
            impersonate=impersonate,
            proxy=proxy,
            follow_redirects=follow_redirects,
        )


async def download_image(url: str, timeout: int = 30) -> Tuple[bytes, str]:
    """Download an image from a URL and return content and content type.

    Uses the unified session interface that works with both curl_cffi and httpx.
    """
    async with create_session(timeout=timeout) as session:
        response = await session.request("GET", url)
        content_type = response.headers.get("content-type", "image/jpeg")

        # Read the response content
        content = b""
        async for chunk in response.aiter_bytes():
            content += chunk

        return content, content_type


# Export the appropriate exception class
if CURL_CFFI_AVAILABLE:
    RequestException = CurlRequestException
else:
    RequestException = httpx.RequestError
