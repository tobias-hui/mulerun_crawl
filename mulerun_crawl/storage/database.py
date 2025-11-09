"""数据存储模块 - PostgreSQL"""
import logging
from datetime import datetime
from typing import List, Dict, Optional
import psycopg2
from psycopg2.pool import SimpleConnectionPool
from contextlib import contextmanager

from ..config import DATABASE_CONFIG

logger = logging.getLogger(__name__)


class DatabaseStorage:
    """PostgreSQL 数据库存储类"""
    
    def __init__(self):
        self.pool = None
        self._init_pool()
        self._init_tables()
    
    def _init_pool(self):
        """初始化连接池"""
        try:
            # 如果使用连接字符串（Neon 等）
            if 'dsn' in DATABASE_CONFIG:
                self.pool = SimpleConnectionPool(
                    minconn=1,
                    maxconn=10,
                    dsn=DATABASE_CONFIG['dsn']
                )
            else:
                # 使用传统参数方式
                self.pool = SimpleConnectionPool(
                    minconn=1,
                    maxconn=10,
                    **DATABASE_CONFIG
                )
            logger.info("数据库连接池初始化成功")
        except Exception as e:
            logger.error(f"数据库连接池初始化失败: {e}")
            raise
    
    @contextmanager
    def get_connection(self):
        """获取数据库连接的上下文管理器"""
        conn = self.pool.getconn()
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"数据库操作失败: {e}")
            raise
        finally:
            self.pool.putconn(conn)
    
    def _init_tables(self):
        """初始化数据库表"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 创建 agents 表（当前状态）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS agents (
                    id SERIAL PRIMARY KEY,
                    link TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    avatar_url TEXT,
                    price TEXT,
                    author TEXT,
                    rank INTEGER NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 创建 rank_history 表（历史排名）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS rank_history (
                    id SERIAL PRIMARY KEY,
                    agent_link TEXT NOT NULL REFERENCES agents(link) ON DELETE CASCADE,
                    rank INTEGER NOT NULL,
                    crawl_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 创建索引
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_agents_link ON agents(link)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_agents_rank ON agents(rank)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_agents_active ON agents(is_active)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_rank_history_link ON rank_history(agent_link)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_rank_history_time ON rank_history(crawl_time)
            """)
            
            conn.commit()
            logger.info("数据库表初始化完成")
    
    def save_agents(self, agents: List[Dict], crawl_time: datetime = None):
        """
        保存 agent 数据
        
        Args:
            agents: agent 数据列表，每个元素包含：
                - link: agent 链接（唯一标识）
                - name: 名称
                - description: 描述
                - avatar_url: 头像 URL
                - price: 价格信息
                - author: 作者
                - rank: 排名
            crawl_time: 爬取时间，默认为当前时间
        """
        if crawl_time is None:
            crawl_time = datetime.now()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 获取当前所有活跃的 agent links
            cursor.execute("SELECT link FROM agents WHERE is_active = TRUE")
            existing_links = {row[0] for row in cursor.fetchall()}
            
            # 当前爬取的 agent links
            current_links = {agent['link'] for agent in agents}
            
            # 标记下架的 agents（存在于数据库但不在当前爬取结果中）
            disappeared_links = existing_links - current_links
            if disappeared_links:
                cursor.execute("""
                    UPDATE agents 
                    SET is_active = FALSE, last_updated = %s
                    WHERE link = ANY(%s)
                """, (crawl_time, list(disappeared_links)))
                logger.info(f"标记了 {len(disappeared_links)} 个下架的 agents")
            
            # 插入或更新 agents
            for agent in agents:
                cursor.execute("""
                    INSERT INTO agents (
                        link, name, description, avatar_url, price, author, rank,
                        is_active, last_updated
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, TRUE, %s)
                    ON CONFLICT (link) 
                    DO UPDATE SET
                        name = EXCLUDED.name,
                        description = EXCLUDED.description,
                        avatar_url = EXCLUDED.avatar_url,
                        price = EXCLUDED.price,
                        author = EXCLUDED.author,
                        rank = EXCLUDED.rank,
                        is_active = TRUE,
                        last_updated = EXCLUDED.last_updated
                """, (
                    agent['link'],
                    agent['name'],
                    agent.get('description'),
                    agent.get('avatar_url'),
                    agent.get('price'),
                    agent.get('author'),
                    agent['rank'],
                    crawl_time
                ))
                
                # 记录排名历史
                cursor.execute("""
                    INSERT INTO rank_history (agent_link, rank, crawl_time)
                    VALUES (%s, %s, %s)
                """, (agent['link'], agent['rank'], crawl_time))
            
            logger.info(f"成功保存 {len(agents)} 个 agents")
    
    def get_active_agents(self, limit: Optional[int] = None) -> List[Dict]:
        """获取所有活跃的 agents"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM agents WHERE is_active = TRUE ORDER BY rank ASC"
            if limit:
                query += f" LIMIT {limit}"
            cursor.execute(query)
            
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def get_rank_history(self, agent_link: str) -> List[Dict]:
        """获取某个 agent 的排名历史"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT rank, crawl_time 
                FROM rank_history 
                WHERE agent_link = %s 
                ORDER BY crawl_time ASC
            """, (agent_link,))
            
            return [
                {'rank': row[0], 'crawl_time': row[1]}
                for row in cursor.fetchall()
            ]
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 活跃 agents 数量
            cursor.execute("SELECT COUNT(*) FROM agents WHERE is_active = TRUE")
            active_count = cursor.fetchone()[0]
            
            # 下架 agents 数量
            cursor.execute("SELECT COUNT(*) FROM agents WHERE is_active = FALSE")
            inactive_count = cursor.fetchone()[0]
            
            # 总爬取次数
            cursor.execute("SELECT COUNT(DISTINCT crawl_time) FROM rank_history")
            crawl_count = cursor.fetchone()[0]
            
            # 最新爬取时间
            cursor.execute("SELECT MAX(crawl_time) FROM rank_history")
            latest_crawl = cursor.fetchone()[0]
            
            return {
                'active_agents': active_count,
                'inactive_agents': inactive_count,
                'total_crawls': crawl_count,
                'latest_crawl': latest_crawl,
            }
    
    def close(self):
        """关闭连接池"""
        if self.pool:
            self.pool.closeall()
            logger.info("数据库连接池已关闭")

