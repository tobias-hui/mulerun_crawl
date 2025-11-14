"""爬取服务"""
import logging
import asyncio
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any

from mulerun_crawl.crawler import crawl_agents
from mulerun_crawl.storage import DatabaseStorage
from mulerun_crawl.notifications import FeishuNotifier
from .task_service import task_service, TaskStatus

logger = logging.getLogger(__name__)

# 线程池执行器（用于运行同步爬虫代码）
executor = ThreadPoolExecutor(max_workers=1)


async def run_crawl_task(task_id: str) -> Dict[str, Any]:
    """
    执行爬取任务（异步包装同步代码）
    
    Args:
        task_id: 任务 ID
        
    Returns:
        任务结果字典
    """
    try:
        task_service.start_task(task_id)
        logger.info(f"开始执行爬取任务: {task_id}")
        
        # 在线程池中运行同步爬虫代码
        loop = asyncio.get_event_loop()
        agents = await loop.run_in_executor(executor, crawl_agents)
        
        if not agents:
            raise Exception("未爬取到任何数据")
        
        # 保存数据
        storage = DatabaseStorage()
        try:
            crawl_time = datetime.now()
            removed_agents, new_agents = storage.save_agents(agents, crawl_time)
            
            # 获取统计信息
            stats = storage.get_statistics()
            
            # 发送飞书通知
            notifier = FeishuNotifier()
            if removed_agents:
                notifier.send_agent_removed_notification(removed_agents)
            if new_agents:
                notifier.send_agent_added_notification(new_agents)
            notifier.send_crawl_summary(stats, crawl_time)
            
            result = {
                "agents_count": len(agents),
                "statistics": stats,
                "removed_agents_count": len(removed_agents),
                "new_agents_count": len(new_agents)
            }
            
            task_service.complete_task(task_id, result)
            logger.info(f"爬取任务完成: {task_id}, 爬取到 {len(agents)} 个 agents, 下架 {len(removed_agents)} 个, 新增 {len(new_agents)} 个")
            
            return result
            
        finally:
            storage.close()
            
    except Exception as e:
        error_msg = str(e)
        logger.error(f"爬取任务失败: {task_id}, 错误: {error_msg}", exc_info=True)
        task_service.fail_task(task_id, error_msg)
        raise


def run_crawl_sync() -> Dict[str, Any]:
    """
    同步执行爬取任务（用于定时任务）
    
    Returns:
        任务结果字典
    """
    try:
        logger.info("开始执行定时爬取任务")
        
        # 爬取数据
        agents = crawl_agents()
        
        if not agents:
            raise Exception("未爬取到任何数据")
        
        # 保存数据
        storage = DatabaseStorage()
        try:
            crawl_time = datetime.now()
            removed_agents, new_agents = storage.save_agents(agents, crawl_time)
            
            # 获取统计信息
            stats = storage.get_statistics()
            
            # 发送飞书通知
            notifier = FeishuNotifier()
            if removed_agents:
                notifier.send_agent_removed_notification(removed_agents)
            if new_agents:
                notifier.send_agent_added_notification(new_agents)
            notifier.send_crawl_summary(stats, crawl_time)
            
            result = {
                "agents_count": len(agents),
                "statistics": stats,
                "crawl_time": crawl_time.isoformat(),
                "removed_agents_count": len(removed_agents),
                "new_agents_count": len(new_agents)
            }
            
            logger.info(f"定时爬取任务完成, 爬取到 {len(agents)} 个 agents, 下架 {len(removed_agents)} 个, 新增 {len(new_agents)} 个")
            return result
            
        finally:
            storage.close()
            
    except Exception as e:
        logger.error(f"定时爬取任务失败: {e}", exc_info=True)
        raise

