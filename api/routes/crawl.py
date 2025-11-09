"""爬取控制路由"""
import asyncio
import logging
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse

from ..models.schemas import CrawlRequest, CrawlResponse, TaskStatus
from ..services.task_service import task_service
from ..services.crawl_service import run_crawl_task

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/start", response_model=CrawlResponse)
async def start_crawl(request: CrawlRequest, background_tasks: BackgroundTasks):
    """
    启动爬取任务
    
    - **async_mode**: 是否异步执行（默认 True）
    """
    try:
        # 创建任务
        task_id = task_service.create_task()
        
        if request.async_mode:
            # 异步执行
            background_tasks.add_task(run_crawl_task, task_id)
            return CrawlResponse(
                task_id=task_id,
                message="爬取任务已启动（异步执行）",
                status="pending"
            )
        else:
            # 同步执行（不推荐，会阻塞请求）
            try:
                result = await run_crawl_task(task_id)
                return CrawlResponse(
                    task_id=task_id,
                    message=f"爬取完成，共爬取 {result['agents_count']} 个 agents",
                    status="completed"
                )
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
                
    except Exception as e:
        logger.error(f"启动爬取任务失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"启动爬取任务失败: {str(e)}")


@router.get("/status/{task_id}", response_model=TaskStatus)
async def get_crawl_status(task_id: str):
    """获取爬取任务状态"""
    task = task_service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    return TaskStatus(**task)

