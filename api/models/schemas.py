"""Pydantic 数据模型"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class AgentInfo(BaseModel):
    """Agent 信息模型"""
    id: Optional[int] = None
    link: str
    name: str
    description: Optional[str] = None
    avatar_url: Optional[str] = None
    price: Optional[str] = None
    author: Optional[str] = None
    rank: int
    is_active: bool = True
    first_seen: Optional[datetime] = None
    last_updated: Optional[datetime] = None


class RankHistory(BaseModel):
    """排名历史模型"""
    rank: int
    crawl_time: datetime


class Statistics(BaseModel):
    """统计信息模型"""
    active_agents: int
    inactive_agents: int
    total_crawls: int
    latest_crawl: Optional[datetime] = None


class TaskStatus(BaseModel):
    """任务状态模型"""
    task_id: str
    status: str = Field(..., description="任务状态: pending, running, completed, failed")
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    result: Optional[Dict[str, Any]] = None


class CrawlRequest(BaseModel):
    """爬取请求模型"""
    async_mode: bool = Field(True, description="是否异步执行")


class CrawlResponse(BaseModel):
    """爬取响应模型"""
    task_id: Optional[str] = None
    message: str
    status: str


class TaskListResponse(BaseModel):
    """任务列表响应"""
    tasks: List[TaskStatus]
    total: int


class SchedulerConfig(BaseModel):
    """定时任务配置模型"""
    enabled: bool
    interval_hours: int = Field(..., ge=1, le=168, description="执行间隔（小时）")
    timezone: str = "Asia/Shanghai"


class SchedulerStatus(BaseModel):
    """定时任务状态模型"""
    enabled: bool
    interval_hours: int
    timezone: str
    next_run_time: Optional[datetime] = None
    last_run_time: Optional[datetime] = None

