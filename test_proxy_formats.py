#!/usr/bin/env python3
"""Test various proxy URL formats"""

import asyncio
from app.utils.proxy import parse_proxy_url, validate_proxy_url
from loguru import logger

def test_proxy_parsing():
    """Test proxy URL parsing with various formats"""
    test_cases = [
        # Format: (input, expected_output)
        ("http://127.0.0.1:7890", "http://127.0.0.1:7890"),
        ("http://user:pass@127.0.0.1:7890", "http://user:pass@127.0.0.1:7890"),
        ("http://127.0.0.1:7890:user:pass", "http://user:pass@127.0.0.1:7890"),
        ("http://38.46.25.24:44001:qz5852c53800396:tsKIlMZNvud9zhRBUl", 
         "http://qz5852c53800396:tsKIlMZNvud9zhRBUl@38.46.25.24:44001"),
        ("socks5://127.0.0.1:1080", "socks5://127.0.0.1:1080"),
        ("socks5://user:pass@127.0.0.1:1080", "socks5://user:pass@127.0.0.1:1080"),
        ("socks5://127.0.0.1:1080:user:pass", "socks5://user:pass@127.0.0.1:1080"),
    ]
    
    logger.info("Testing proxy URL parsing...")
    for input_url, expected in test_cases:
        result = parse_proxy_url(input_url)
        if result == expected:
            logger.success(f"✓ {input_url} -> {result}")
        else:
            logger.error(f"✗ {input_url} -> {result} (expected: {expected})")
    
    # Test validation
    logger.info("\nTesting proxy URL validation...")
    valid_urls = [
        "http://127.0.0.1:7890",
        "http://user:pass@127.0.0.1:7890",
        "socks5://127.0.0.1:1080",
    ]
    
    invalid_urls = [
        "ftp://127.0.0.1:21",  # Invalid protocol
        "http://127.0.0.1",     # Missing port
        "http://127.0.0.1:99999",  # Invalid port
    ]
    
    for url in valid_urls:
        is_valid, error = validate_proxy_url(parse_proxy_url(url))
        if is_valid:
            logger.success(f"✓ {url} is valid")
        else:
            logger.error(f"✗ {url} validation failed: {error}")
    
    for url in invalid_urls:
        is_valid, error = validate_proxy_url(url)
        if not is_valid:
            logger.success(f"✓ {url} correctly identified as invalid: {error}")
        else:
            logger.error(f"✗ {url} should be invalid but passed validation")

async def test_proxy_connection():
    """Test actual proxy connection with http_client"""
    from app.core.http_client import create_session
    
    # Test with the problematic format
    test_proxy = "http://38.46.25.24:44001:qz5852c53800396:tsKIlMZNvud9zhRBUl"
    
    logger.info(f"\nTesting proxy connection with: {test_proxy}")
    
    try:
        async with create_session(proxy=test_proxy) as session:
            # Try to make a simple request
            response = await session.request("GET", "http://httpbin.org/ip")
            data = await response.ajson()
            logger.success(f"Proxy connection successful! Response: {data}")
    except Exception as e:
        logger.error(f"Proxy connection failed: {e}")
        logger.info("This might be because the proxy server is not reachable or requires valid credentials")

if __name__ == "__main__":
    # Test parsing and validation
    test_proxy_parsing()
    
    # Test actual connection
    asyncio.run(test_proxy_connection())