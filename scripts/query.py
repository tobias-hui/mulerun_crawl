"""数据查询工具脚本"""
import argparse
import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from mulerun_crawl.storage import DatabaseStorage
from mulerun_crawl.utils import setup_logging
import logging

logger = logging.getLogger(__name__)


def format_timestamp(ts):
    """格式化时间戳"""
    if ts:
        return ts.strftime('%Y-%m-%d %H:%M:%S')
    return None


def list_agents(args):
    """列出 agents"""
    storage = DatabaseStorage()
    
    try:
        if args.active_only:
            agents = storage.get_active_agents(limit=args.limit)
            print(f"\n活跃 Agents (共 {len(agents)} 个):\n")
        else:
            # 获取所有 agents（包括下架的）
            with storage.get_connection() as conn:
                cursor = conn.cursor()
                query = "SELECT * FROM agents ORDER BY rank ASC"
                if args.limit:
                    query += f" LIMIT {args.limit}"
                cursor.execute(query)
                columns = [desc[0] for desc in cursor.description]
                agents = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            active_count = sum(1 for a in agents if a['is_active'])
            print(f"\n所有 Agents (共 {len(agents)} 个，活跃 {active_count} 个):\n")
        
        for agent in agents:
            status = "✓" if agent['is_active'] else "✗"
            print(f"{status} [{agent['rank']:4d}] {agent['name']}")
            print(f"     链接: {agent['link']}")
            print(f"     作者: {agent['author']}")
            print(f"     价格: {agent['price']}")
            if agent['description']:
                desc = agent['description'][:80] + "..." if len(agent['description']) > 80 else agent['description']
                print(f"     描述: {desc}")
            print(f"     最后更新: {format_timestamp(agent['last_updated'])}")
            print()
    
    finally:
        storage.close()


def show_rank_history(args):
    """显示排名历史"""
    storage = DatabaseStorage()
    
    try:
        history = storage.get_rank_history(args.link)
        
        if not history:
            print(f"未找到 agent {args.link} 的排名历史")
            return
        
        # 获取 agent 基本信息
        with storage.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name, author FROM agents WHERE link = %s", (args.link,))
            result = cursor.fetchone()
            if result:
                name, author = result
                print(f"\nAgent: {name}")
                print(f"作者: {author}")
                print(f"链接: {args.link}\n")
        
        print("排名历史:")
        print("-" * 50)
        print(f"{'时间':<20} {'排名':<10} {'变化':<10}")
        print("-" * 50)
        
        prev_rank = None
        for record in history:
            change = ""
            if prev_rank is not None:
                diff = prev_rank - record['rank']
                if diff > 0:
                    change = f"↑{diff}"
                elif diff < 0:
                    change = f"↓{abs(diff)}"
                else:
                    change = "→"
            prev_rank = record['rank']
            
            print(f"{format_timestamp(record['crawl_time']):<20} {record['rank']:<10} {change:<10}")
    
    finally:
        storage.close()


def show_statistics(args):
    """显示统计信息"""
    storage = DatabaseStorage()
    
    try:
        stats = storage.get_statistics()
        
        print("\n" + "=" * 50)
        print("统计信息")
        print("=" * 50)
        print(f"活跃 Agents:     {stats['active_agents']}")
        print(f"下架 Agents:     {stats['inactive_agents']}")
        print(f"总爬取次数:      {stats['total_crawls']}")
        print(f"最新爬取时间:    {format_timestamp(stats['latest_crawl'])}")
        print("=" * 50)
        
        # 显示排名变化最大的 agents
        if args.show_changes:
            print("\n排名变化最大的 Agents (最近两次爬取):")
            with storage.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    WITH latest_two AS (
                        SELECT DISTINCT crawl_time 
                        FROM rank_history 
                        ORDER BY crawl_time DESC 
                        LIMIT 2
                    ),
                    latest_ranks AS (
                        SELECT rh1.agent_link, rh1.rank as latest_rank, rh2.rank as prev_rank
                        FROM rank_history rh1
                        JOIN rank_history rh2 ON rh1.agent_link = rh2.agent_link
                        JOIN latest_two lt1 ON rh1.crawl_time = lt1.crawl_time
                        JOIN latest_two lt2 ON rh2.crawl_time = lt2.crawl_time
                        WHERE rh1.crawl_time > rh2.crawl_time
                        AND NOT EXISTS (
                            SELECT 1 FROM rank_history rh3
                            WHERE rh3.agent_link = rh1.agent_link
                            AND rh3.crawl_time > rh2.crawl_time
                            AND rh3.crawl_time < rh1.crawl_time
                        )
                    )
                    SELECT a.name, a.link, lt.latest_rank, lt.prev_rank, 
                           (lt.prev_rank - lt.latest_rank) as rank_change
                    FROM latest_ranks lt
                    JOIN agents a ON lt.agent_link = a.link
                    ORDER BY ABS(rank_change) DESC
                    LIMIT 10
                """)
                
                results = cursor.fetchall()
                if results:
                    print(f"{'名称':<30} {'最新排名':<10} {'上次排名':<10} {'变化':<10}")
                    print("-" * 60)
                    for name, link, latest, prev, change in results:
                        change_str = f"↑{change}" if change > 0 else f"↓{abs(change)}" if change < 0 else "→"
                        print(f"{name[:28]:<30} {latest:<10} {prev:<10} {change_str:<10}")
                else:
                    print("暂无数据")
    
    finally:
        storage.close()


def main():
    parser = argparse.ArgumentParser(description='MuleRun Agent 数据查询工具')
    subparsers = parser.add_subparsers(dest='command', help='命令')
    
    # list 命令
    list_parser = subparsers.add_parser('list', help='列出 agents')
    list_parser.add_argument('--active-only', action='store_true', help='只显示活跃的 agents')
    list_parser.add_argument('--limit', type=int, help='限制返回数量')
    
    # history 命令
    history_parser = subparsers.add_parser('history', help='查看排名历史')
    history_parser.add_argument('link', help='Agent 链接（如 /@laughing_code/chibi-sticker-maker）')
    
    # stats 命令
    stats_parser = subparsers.add_parser('stats', help='显示统计信息')
    stats_parser.add_argument('--show-changes', action='store_true', help='显示排名变化最大的 agents')
    
    args = parser.parse_args()
    
    setup_logging()
    
    if args.command == 'list':
        list_agents(args)
    elif args.command == 'history':
        show_rank_history(args)
    elif args.command == 'stats':
        show_statistics(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

