"""数据查询路由"""
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query, Security

from ..models.schemas import AgentInfo, Statistics, RankHistory
from mulerun_crawl.storage import DatabaseStorage
from ..middleware.auth import verify_api_key

router = APIRouter()


@router.get("/", response_model=List[AgentInfo])
async def list_agents(
    active_only: bool = Query(True, description="是否只返回活跃的 agents"),
    limit: Optional[int] = Query(None, ge=1, le=1000, description="返回数量限制"),
    api_key: str = Security(verify_api_key)
):
    """
    获取 agents 列表
    
    - **active_only**: 是否只返回活跃的 agents（默认 True）
    - **limit**: 返回数量限制（可选）
    """
    try:
        storage = DatabaseStorage()
        try:
            if active_only:
                agents = storage.get_active_agents(limit=limit)
            else:
                agents = storage.get_all_agents(limit=limit)
            
            return [AgentInfo(**agent) for agent in agents]
        finally:
            storage.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.get("/{agent_link:path}/history", response_model=List[RankHistory])
async def get_agent_history(
    agent_link: str,
    api_key: str = Security(verify_api_key)
):
    """
    获取指定 agent 的排名历史
    
    - **agent_link**: agent 链接（URL 路径格式，如 /@user/agent-name）
    """
    try:
        storage = DatabaseStorage()
        try:
            history = storage.get_rank_history(agent_link)
            return [RankHistory(**item) for item in history]
        finally:
            storage.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.get("/statistics", response_model=Statistics)
async def get_statistics(api_key: str = Security(verify_api_key)):
    """获取统计信息"""
    try:
        storage = DatabaseStorage()
        try:
            stats = storage.get_statistics()
            return Statistics(**stats)
        finally:
            storage.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")

