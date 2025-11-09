"""配置文件"""
import os
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 项目根目录（相对于包的位置）
BASE_DIR = Path(__file__).parent.parent

# 数据库配置
# 优先使用 DATABASE_URL（Neon 等云数据库连接字符串）
DATABASE_URL = os.getenv('DATABASE_URL')

if DATABASE_URL:
    # 使用连接字符串（Neon 等）
    DATABASE_CONFIG = {
        'dsn': DATABASE_URL,
    }
else:
    # 使用传统配置方式
    DATABASE_CONFIG = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', 5432)),
        'database': os.getenv('DB_DATABASE', 'mulerun_crawl'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', ''),
    }

# 爬虫配置
CRAWLER_CONFIG = {
    'base_url': 'https://mulerun.com/',
    'sort_mode': 'most_used',  # 只爬取 Most used 排序
    'scroll_timeout': 30,  # 滚动超时时间（秒）
    'scroll_delay': 2,  # 每次滚动后的等待时间（秒）
    'max_scroll_attempts': 50,  # 最大滚动次数
    'no_new_content_threshold': 3,  # 连续几次没有新内容则停止
    'headless': True,  # 无头模式（VPS 环境推荐）
    'user_agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'page_load_timeout': 60000,  # 页面加载超时时间（毫秒），默认60秒
    'page_wait_strategy': 'load',  # 页面等待策略：'load', 'domcontentloaded', 'networkidle'
    'max_retries': 3,  # 最大重试次数
    'retry_delay': 5,  # 重试延迟（秒）
}

# 定时任务配置
SCHEDULER_CONFIG = {
    'interval_hours': 24,  # 每24小时执行一次
    'timezone': 'Asia/Shanghai',  # 时区
}

# 日志配置
LOG_CONFIG = {
    'level': 'INFO',
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'file': BASE_DIR / 'logs' / 'crawler.log',
    'max_bytes': 10 * 1024 * 1024,  # 10MB
    'backup_count': 5,
}

