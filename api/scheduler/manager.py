"""定时任务调度器管理"""
import logging
from datetime import datetime
from typing import Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from mulerun_crawl.config import SCHEDULER_CONFIG
from ..services.crawl_service import run_crawl_sync

logger = logging.getLogger(__name__)


class SchedulerManager:
    """定时任务调度器管理器"""
    
    def __init__(self):
        self.scheduler: Optional[AsyncIOScheduler] = None
        self.enabled = False
        self.interval_hours = SCHEDULER_CONFIG['interval_hours']
        self.timezone = SCHEDULER_CONFIG['timezone']
        self.last_run_time: Optional[datetime] = None
    
    def start(self, enabled: bool = True):
        """
        启动调度器
        
        Args:
            enabled: 是否启用定时任务（默认 True）
        """
        if self.scheduler and self.scheduler.running:
            logger.warning("调度器已在运行")
            return
        
        self.enabled = enabled
        
        # 创建异步调度器
        self.scheduler = AsyncIOScheduler(timezone=self.timezone)
        
        if enabled:
            # 添加定时任务
            self.scheduler.add_job(
                self._crawl_job,
                trigger=IntervalTrigger(hours=self.interval_hours),
                id='crawl_job',
                name='MuleRun 定时爬取任务',
                replace_existing=True,
                max_instances=1  # 防止任务重叠
            )
            logger.info(f"定时任务已添加，每 {self.interval_hours} 小时执行一次")
        
        # 启动调度器
        self.scheduler.start()
        logger.info("调度器已启动")
    
    def stop(self):
        """停止调度器"""
        if self.scheduler and self.scheduler.running:
            self.scheduler.shutdown()
            self.enabled = False
            logger.info("调度器已停止")
        else:
            logger.warning("调度器未运行")
    
    def shutdown(self):
        """关闭调度器（应用关闭时调用）"""
        self.stop()
    
    def update_config(self, interval_hours: Optional[int] = None, enabled: Optional[bool] = None):
        """
        更新配置
        
        Args:
            interval_hours: 执行间隔（小时）
            enabled: 是否启用
        """
        if interval_hours is not None:
            self.interval_hours = interval_hours
        
        if enabled is not None:
            self.enabled = enabled
        
        # 如果调度器正在运行，需要重启以应用新配置
        if self.scheduler and self.scheduler.running:
            self.stop()
            self.start(self.enabled)
        elif enabled:
            # 如果调度器未运行但需要启用，则启动
            self.start(self.enabled)
    
    def get_status(self) -> dict:
        """获取调度器状态"""
        next_run_time = None
        if self.scheduler and self.scheduler.running:
            job = self.scheduler.get_job('crawl_job')
            if job:
                next_run_time = job.next_run_time
        
        return {
            "enabled": self.enabled,
            "interval_hours": self.interval_hours,
            "timezone": self.timezone,
            "next_run_time": next_run_time,
            "last_run_time": self.last_run_time
        }
    
    async def _crawl_job(self):
        """定时爬取任务（异步包装）"""
        try:
            logger.info("=" * 50)
            logger.info("开始执行定时爬取任务")
            
            # 在线程池中运行同步爬虫代码
            import asyncio
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, run_crawl_sync)
            
            self.last_run_time = datetime.now()
            
            logger.info(f"定时爬取任务完成: {result}")
            logger.info("=" * 50)
            
        except Exception as e:
            self.last_run_time = datetime.now()
            logger.error(f"定时爬取任务执行失败: {e}", exc_info=True)


# 全局调度器管理器实例
scheduler_manager = SchedulerManager()

