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

try:
    import rnet
    from rnet import Client as RnetClient, Method as RnetMethod
    from rnet.exceptions import RequestError as RnetRequestError

    RNET_AVAILABLE = True
except ImportError:
    RNET_AVAILABLE = False

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

if not RNET_AVAILABLE and not CURL_CFFI_AVAILABLE and not HTTPX_AVAILABLE:
    raise ImportError(
        "Neither rnet, curl_cffi nor httpx is installed. Please install at least one of them."
    )


class Response(ABC):
    """Abstract response class."""

    @property
    @abstractmethod
    def status_code(self) -> int:
        """Get response status code."""
        pass

    @abstractmethod
    async def json(self) -> Any:
        """Parse response as JSON."""
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
        self._stream = stream

    @property
    def status_code(self) -> int:
        return self._response.status_code

    async def json(self) -> Any:
        if self._stream:
            content = ""
            async for chunk in self._response.aiter_content():
                content += chunk.decode("utf-8")
            return json.loads(content)
        else:
            return self._response.json()

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

    async def json(self) -> Any:
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


if RNET_AVAILABLE:

    class RnetResponse(Response):
        """rnet response wrapper."""

        def __init__(self, response: "rnet.Response"):
            self._response = response

        @property
        def status_code(self) -> int:
            return self._response.status.as_int()

        async def json(self) -> Any:
            return await self._response.json()

        @property
        def headers(self) -> Dict[str, str]:
            headers_dict = {}
            for key, value in self._response.headers:
                key_str = key.decode("utf-8") if isinstance(key, bytes) else key
                value_str = value.decode("utf-8") if isinstance(value, bytes) else value
                headers_dict[key_str] = value_str
            return headers_dict

        async def aiter_bytes(
            self, chunk_size: Optional[int] = None
        ) -> AsyncIterator[bytes]:
            async with self._response.stream() as streamer:
                async for chunk in streamer:
                    yield chunk
            await self._response.close()


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
                return CurlResponseWrapper(response, stream=stream)
            finally:
                if multipart:
                    multipart.close()

        async def close(self):
            await self._session.close()


if RNET_AVAILABLE:

    class RnetAsyncSession(AsyncSession):
        """rnet async session wrapper."""

        def __init__(
            self,
            timeout: int = settings.request_timeout,
            impersonate: str = "chrome",
            proxy: Optional[str] = settings.proxy_url,
            follow_redirects: bool = True,
        ):
            # Map impersonate string to rnet Emulation enum
            emulation_map = {
                "chrome": rnet.Emulation.Chrome142,
                "firefox": rnet.Emulation.Firefox136,
                "safari": rnet.Emulation.Safari18,
                "edge": rnet.Emulation.Edge134,
            }

            # Use Chrome as default if not found in map
            rnet_emulation = emulation_map.get(
                impersonate.lower(), rnet.Emulation.Chrome142
            )

            # Create proxy list if proxy is provided
            proxies = None
            if proxy:
                proxies = [rnet.Proxy.all(proxy)]

            self._client = RnetClient(
                emulation=rnet_emulation,
                timeout=timeout,
                proxies=proxies,
                allow_redirects=follow_redirects,
            )

        @retry(
            stop=stop_after_attempt(settings.request_retries),
            wait=wait_fixed(settings.request_retry_interval),
            retry=retry_if_exception_type(RnetRequestError),
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

            # Map method string to rnet Method enum
            method_map = {
                "GET": RnetMethod.GET,
                "POST": RnetMethod.POST,
                "PUT": RnetMethod.PUT,
                "DELETE": RnetMethod.DELETE,
                "PATCH": RnetMethod.PATCH,
                "HEAD": RnetMethod.HEAD,
                "OPTIONS": RnetMethod.OPTIONS,
                "TRACE": RnetMethod.TRACE,
            }

            rnet_method = method_map.get(method.upper(), RnetMethod.GET)

            # Handle file uploads - convert files parameter to multipart
            files = kwargs.pop("files", None)
            multipart = None

            if files:
                # Convert files dict to rnet Multipart
                parts = []
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

                        parts.append(
                            rnet.Part(
                                name=field_name,
                                value=file_data,
                                filename=filename,
                                mime=content_type,
                            )
                        )
                    else:
                        # Simple format: {"field": data}
                        parts.append(rnet.Part(name=field_name, value=file_info))

                multipart = rnet.Multipart(*parts)
                kwargs["multipart"] = multipart

            request_kwargs = {}
            if headers:
                request_kwargs["headers"] = headers
            if json is not None:
                request_kwargs["json"] = json
            elif data is not None:
                # rnet uses 'form' for form data, 'body' for raw data
                if isinstance(data, dict) or isinstance(data, list):
                    request_kwargs["form"] = (
                        [(k, v) for k, v in data.items()]
                        if isinstance(data, dict)
                        else data
                    )
                else:
                    request_kwargs["body"] = data

            request_kwargs.update(kwargs)

            response = await self._client.request(
                method=rnet_method,
                url=url,
                **request_kwargs,
            )

            return RnetResponse(response)

        async def close(self):
            # rnet Client doesn't have an explicit close method
            # The connection pooling is handled internally
            pass


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
            self._client = httpx.AsyncClient(
                timeout=timeout,
                proxy=proxy,
                follow_redirects=follow_redirects,
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

    Prefers rnet if available, then curl_cffi, falls back to httpx.
    """
    if RNET_AVAILABLE:
        logger.debug("Using rnet as HTTP client")
        return RnetAsyncSession(
            timeout=timeout,
            impersonate=impersonate,
            proxy=proxy,
            follow_redirects=follow_redirects,
        )
    elif CURL_CFFI_AVAILABLE:
        logger.debug("Using curl_cffi as HTTP client")
        return CurlAsyncSessionWrapper(
            timeout=timeout,
            impersonate=impersonate,
            proxy=proxy,
            follow_redirects=follow_redirects,
        )
    else:
        logger.debug("Using httpx as HTTP client (rnet and curl_cffi not available)")
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
if RNET_AVAILABLE:
    RequestException = RnetRequestError
elif CURL_CFFI_AVAILABLE:
    RequestException = CurlRequestException
else:
    RequestException = httpx.RequestError
