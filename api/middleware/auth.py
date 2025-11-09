"""API Key 认证中间件"""
import os
import logging
from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader

logger = logging.getLogger(__name__)

# API Key Header 名称
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

# 从环境变量读取 API Key
API_KEY = os.getenv("API_KEY", "")

# 如果未设置 API_KEY，则不启用验证（开发模式）
ENABLE_AUTH = bool(API_KEY)


async def verify_api_key(api_key: str = Security(API_KEY_HEADER)):
    """
    验证 API Key
    
    Args:
        api_key: 从请求头获取的 API Key
        
    Returns:
        str: 验证通过返回 API Key
        
    Raises:
        HTTPException: API Key 无效或缺失
    """
    # 如果未启用认证，直接通过
    if not ENABLE_AUTH:
        return api_key or "no-auth"
    
    # 检查 API Key 是否存在
    if not api_key:
        logger.warning("API Key 缺失")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key 缺失。请在请求头中添加 'X-API-Key'",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    # 验证 API Key
    if api_key != API_KEY:
        logger.warning(f"API Key 验证失败: {api_key[:10]}...")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API Key 无效",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    logger.debug("API Key 验证通过")
    return api_key

