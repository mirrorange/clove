"""Proxy URL parsing and formatting utilities."""

import re
from typing import Optional, Tuple
from urllib.parse import urlparse, urlunparse


def parse_proxy_url(proxy_url: str) -> str:
    """
    Parse and convert various proxy URL formats to standard format.
    
    Supported formats:
    - http://ip:port
    - http://username:password@ip:port
    - http://ip:port:username:password
    - socks5://ip:port
    - socks5://username:password@ip:port
    - socks5://ip:port:username:password
    
    Returns:
    - Standard format: protocol://username:password@ip:port
    """
    if not proxy_url:
        return proxy_url
    
    # Remove any trailing slashes
    proxy_url = proxy_url.rstrip('/')
    
    # Pattern for non-standard format: protocol://ip:port:username:password
    non_standard_pattern = r'^(https?|socks5)://([^:]+):(\d+):([^:]+):(.+)$'
    match = re.match(non_standard_pattern, proxy_url)
    
    if match:
        protocol, ip, port, username, password = match.groups()
        # Convert to standard format
        return f"{protocol}://{username}:{password}@{ip}:{port}"
    
    # If already in standard format or simple format without auth, return as is
    return proxy_url


def validate_proxy_url(proxy_url: str) -> Tuple[bool, Optional[str]]:
    """
    Validate a proxy URL.
    
    Returns:
    - (True, None) if valid
    - (False, error_message) if invalid
    """
    if not proxy_url:
        return True, None
    
    try:
        # Parse the proxy URL
        parsed = urlparse(proxy_url)
        
        # Check protocol
        if parsed.scheme not in ['http', 'https', 'socks5']:
            return False, f"Unsupported protocol: {parsed.scheme}"
        
        # Check hostname
        if not parsed.hostname:
            return False, "Missing hostname/IP address"
        
        # Check port
        if not parsed.port:
            return False, "Missing port number"
        
        if parsed.port < 0 or parsed.port > 65535:
            return False, f"Invalid port number: {parsed.port}"
        
        return True, None
        
    except Exception as e:
        return False, f"Invalid proxy URL: {str(e)}"


def get_curl_proxy_url(proxy_url: str) -> str:
    """
    Convert proxy URL to format suitable for curl_cffi.
    curl_cffi supports standard proxy URL format including SOCKS5.
    """
    parsed_url = parse_proxy_url(proxy_url)
    # curl_cffi supports socks5:// directly
    return parsed_url


def get_httpx_proxy_url(proxy_url: str) -> str:
    """
    Convert proxy URL to format suitable for httpx.
    httpx supports HTTP/HTTPS proxies but requires httpx-socks for SOCKS5.
    """
    parsed_url = parse_proxy_url(proxy_url)
    
    # Check if it's a SOCKS5 proxy
    if parsed_url and parsed_url.startswith('socks5://'):
        # httpx doesn't support SOCKS5 natively, would need httpx-socks
        # For now, we'll let httpx handle it and it will raise an error if not supported
        pass
    
    return parsed_url