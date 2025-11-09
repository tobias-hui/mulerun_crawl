"""任务管理路由"""
from fastapi import APIRouter, HTTPException, Query, Security
from typing import Optional

from ..models.schemas import TaskListResponse, TaskStatus, SchedulerStatus, SchedulerConfig
from ..services.task_service import task_service
from ..scheduler import scheduler_manager
from ..middleware.auth import verify_api_key

router = APIRouter()


@router.get("/", response_model=TaskListResponse)
async def list_tasks(
    limit: int = Query(50, ge=1, le=1000),
    api_key: str = Security(verify_api_key)
):
    """获取任务列表"""
    tasks = task_service.list_tasks(limit=limit)
    return TaskListResponse(
        tasks=[TaskStatus(**task) for task in tasks],
        total=len(tasks)
    )


@router.get("/{task_id}", response_model=TaskStatus)
async def get_task(task_id: str):
    """获取任务详情"""
    task = task_service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return TaskStatus(**task)


@router.get("/scheduler/status", response_model=SchedulerStatus)
async def get_scheduler_status(api_key: str = Security(verify_api_key)):
    """获取定时任务状态"""
    return scheduler_manager.get_status()


@router.post("/scheduler/start")
async def start_scheduler(api_key: str = Security(verify_api_key)):
    """启动定时任务"""
    try:
        scheduler_manager.start()
        return {"message": "定时任务已启动", "status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"启动失败: {str(e)}")


@router.post("/scheduler/stop")
async def stop_scheduler(api_key: str = Security(verify_api_key)):
    """停止定时任务"""
    try:
        scheduler_manager.stop()
        return {"message": "定时任务已停止", "status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"停止失败: {str(e)}")


@router.put("/scheduler/config", response_model=SchedulerStatus)
async def update_scheduler_config(
    config: SchedulerConfig,
    api_key: str = Security(verify_api_key)
):
    """更新定时任务配置"""
    try:
        scheduler_manager.update_config(
            interval_hours=config.interval_hours,
            enabled=config.enabled
        )
        return scheduler_manager.get_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新配置失败: {str(e)}")

