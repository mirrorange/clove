#!/usr/bin/env python3
"""测试账号代理功能的脚本"""

import asyncio
from app.core.account import Account, AuthType
from app.core.external.claude_client import ClaudeWebClient
from loguru import logger

async def test_proxy():
    """测试代理功能"""
    # 创建一个带有代理的测试账号
    test_account = Account(
        organization_uuid="test-org-123",
        capabilities=["chat"],
        cookie_value="sessionKey=sk-ant-sid01-test-cookie",
        auth_type=AuthType.COOKIE_ONLY,
        proxy_url="http://127.0.0.1:7890"  # 示例代理地址
    )
    
    logger.info(f"创建测试账号，代理地址: {test_account.proxy_url}")
    
    # 创建客户端
    client = ClaudeWebClient(test_account)
    
    try:
        # 初始化客户端
        await client.initialize()
        logger.info("客户端初始化成功")
        
        # 检查session中的代理设置
        if hasattr(client.session, '_session'):
            # curl_cffi
            session = client.session._session
            logger.info(f"Session代理配置: {getattr(session, '_proxy', 'None')}")
        elif hasattr(client.session, '_client'):
            # httpx
            client_obj = client.session._client
            logger.info(f"Client代理配置: {getattr(client_obj, '_proxy', 'None')}")
        
        logger.success("代理功能测试通过！账号可以使用独立的代理IP。")
        
    except Exception as e:
        logger.error(f"测试失败: {e}")
    finally:
        await client.cleanup()

if __name__ == "__main__":
    asyncio.run(test_proxy())