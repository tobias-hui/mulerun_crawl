"""任务管理服务"""
import uuid
import logging
from datetime import datetime
from typing import Dict, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskService:
    """任务管理服务（内存存储，生产环境建议使用 Redis）"""
    
    def __init__(self):
        self.tasks: Dict[str, Dict] = {}
    
    def create_task(self) -> str:
        """创建新任务"""
        task_id = str(uuid.uuid4())
        self.tasks[task_id] = {
            "task_id": task_id,
            "status": TaskStatus.PENDING,
            "created_at": datetime.now(),
            "started_at": None,
            "completed_at": None,
            "error": None,
            "result": None,
        }
        logger.info(f"创建任务: {task_id}")
        return task_id
    
    def get_task(self, task_id: str) -> Optional[Dict]:
        """获取任务信息"""
        return self.tasks.get(task_id)
    
    def update_task(self, task_id: str, **kwargs):
        """更新任务信息"""
        if task_id in self.tasks:
            self.tasks[task_id].update(kwargs)
            logger.debug(f"更新任务 {task_id}: {kwargs}")
    
    def list_tasks(self, limit: int = 50) -> list:
        """列出所有任务（最近 N 个）"""
        tasks = sorted(
            self.tasks.values(),
            key=lambda x: x["created_at"],
            reverse=True
        )
        return tasks[:limit]
    
    def start_task(self, task_id: str):
        """标记任务开始"""
        self.update_task(
            task_id,
            status=TaskStatus.RUNNING,
            started_at=datetime.now()
        )
    
    def complete_task(self, task_id: str, result: Dict):
        """标记任务完成"""
        self.update_task(
            task_id,
            status=TaskStatus.COMPLETED,
            completed_at=datetime.now(),
            result=result
        )
    
    def fail_task(self, task_id: str, error: str):
        """标记任务失败"""
        self.update_task(
            task_id,
            status=TaskStatus.FAILED,
            completed_at=datetime.now(),
            error=error
        )


# 全局任务服务实例
task_service = TaskService()

