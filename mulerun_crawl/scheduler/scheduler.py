"""定时任务模块"""
import logging
import signal
import sys
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger

from ..config import SCHEDULER_CONFIG
from ..crawler import crawl_agents
from ..storage import DatabaseStorage

logger = logging.getLogger(__name__)


class CrawlScheduler:
    """爬虫定时调度器"""
    
    def __init__(self):
        self.scheduler = BlockingScheduler(timezone=SCHEDULER_CONFIG['timezone'])
        self.storage = DatabaseStorage()
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self):
        """设置信号处理器，优雅关闭"""
        def signal_handler(signum, frame):
            logger.info("收到停止信号，正在关闭...")
            self.stop()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def _crawl_job(self):
        """定时爬取任务"""
        try:
            logger.info("=" * 50)
            logger.info("开始执行定时爬取任务")
            crawl_time = datetime.now()
            
            # 爬取数据
            agents = crawl_agents()
            
            if not agents:
                logger.warning("未爬取到任何数据")
                return
            
            # 保存数据
            self.storage.save_agents(agents, crawl_time)
            
            # 输出统计信息
            stats = self.storage.get_statistics()
            logger.info(f"爬取完成！统计信息：")
            logger.info(f"  - 活跃 agents: {stats['active_agents']}")
            logger.info(f"  - 下架 agents: {stats['inactive_agents']}")
            logger.info(f"  - 总爬取次数: {stats['total_crawls']}")
            logger.info(f"  - 最新爬取时间: {stats['latest_crawl']}")
            logger.info("=" * 50)
            
        except Exception as e:
            logger.error(f"定时爬取任务执行失败: {e}", exc_info=True)
    
    def start(self, run_immediately: bool = True):
        """
        启动定时任务
        
        Args:
            run_immediately: 是否立即执行一次
        """
        # 添加定时任务
        self.scheduler.add_job(
            self._crawl_job,
            trigger=IntervalTrigger(hours=SCHEDULER_CONFIG['interval_hours']),
            id='crawl_job',
            name='MuleRun 爬取任务',
            replace_existing=True
        )
        
        # 立即执行一次
        if run_immediately:
            logger.info("立即执行一次爬取任务...")
            self._crawl_job()
        
        logger.info(f"定时任务已启动，每 {SCHEDULER_CONFIG['interval_hours']} 小时执行一次")
        logger.info("按 Ctrl+C 停止")
        
        try:
            self.scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            self.stop()
    
    def stop(self):
        """停止定时任务"""
        logger.info("正在停止定时任务...")
        self.scheduler.shutdown()
        self.storage.close()
        logger.info("定时任务已停止")


def run_scheduler(run_immediately: bool = True):
    """
    运行定时调度器的便捷函数
    
    Args:
        run_immediately: 是否立即执行一次
    """
    scheduler = CrawlScheduler()
    scheduler.start(run_immediately=run_immediately)

