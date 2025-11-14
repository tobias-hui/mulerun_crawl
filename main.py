"""主程序入口"""
import argparse
import logging
from datetime import datetime

from mulerun_crawl.utils import setup_logging
from mulerun_crawl.crawler import crawl_agents
from mulerun_crawl.storage import DatabaseStorage
from mulerun_crawl.scheduler import run_scheduler

logger = logging.getLogger(__name__)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='MuleRun Agent 爬虫')
    parser.add_argument(
        '--mode',
        choices=['once', 'daemon'],
        default='once',
        help='运行模式: once=单次运行, daemon=守护进程模式（定时任务）'
    )
    parser.add_argument(
        '--no-immediate',
        action='store_true',
        help='守护进程模式下，不立即执行一次爬取'
    )
    
    args = parser.parse_args()
    
    # 设置日志
    setup_logging()
    logger.info("=" * 50)
    logger.info("MuleRun Agent 爬虫启动")
    logger.info("=" * 50)
    
    if args.mode == 'once':
        # 单次运行模式
        logger.info("运行模式: 单次运行")
        try:
            # 爬取数据
            agents = crawl_agents()
            
            if not agents:
                logger.warning("未爬取到任何数据")
                return
            
            # 保存数据
            storage = DatabaseStorage()
            crawl_time = datetime.now()
            removed_agents = storage.save_agents(agents, crawl_time)
            
            # 发送飞书通知
            from mulerun_crawl.notifications import FeishuNotifier
            notifier = FeishuNotifier()
            if removed_agents:
                notifier.send_agent_removed_notification(removed_agents)
            notifier.send_crawl_summary(storage.get_statistics(), crawl_time)
            
            # 输出统计信息
            stats = storage.get_statistics()
            logger.info("爬取完成！统计信息：")
            logger.info(f"  - 活跃 agents: {stats['active_agents']}")
            logger.info(f"  - 下架 agents: {stats['inactive_agents']}")
            logger.info(f"  - 本次下架: {len(removed_agents)} 个")
            logger.info(f"  - 总爬取次数: {stats['total_crawls']}")
            logger.info(f"  - 最新爬取时间: {stats['latest_crawl']}")
            
            storage.close()
            
        except KeyboardInterrupt:
            logger.info("\n收到中断信号 (Ctrl+C)，正在退出...")
            logger.info("浏览器资源已清理")
            return
        except Exception as e:
            logger.error(f"执行失败: {e}", exc_info=True)
            raise
    
    elif args.mode == 'daemon':
        # 守护进程模式（定时任务）
        logger.info("运行模式: 守护进程（定时任务）")
        run_immediately = not args.no_immediate
        run_scheduler(run_immediately=run_immediately)


if __name__ == "__main__":
    main()
