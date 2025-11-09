"""FastAPI 应用主文件"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from mulerun_crawl.utils import setup_logging
from .routes import crawl, agents, tasks, health
from .scheduler import scheduler_manager

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    logger.info("FastAPI 应用启动中...")
    setup_logging()
    
    # 启动定时任务调度器
    scheduler_manager.start()
    logger.info("定时任务调度器已启动")
    
    yield
    
    # 关闭时
    logger.info("FastAPI 应用关闭中...")
    scheduler_manager.shutdown()
    logger.info("定时任务调度器已关闭")


# 创建 FastAPI 应用
app = FastAPI(
    title="MuleRun Crawler API",
    description="MuleRun 网站监控和爬取 API",
    version="1.0.0",
    lifespan=lifespan
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应配置具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(health.router, prefix="/api", tags=["健康检查"])
app.include_router(crawl.router, prefix="/api/crawl", tags=["爬取控制"])
app.include_router(agents.router, prefix="/api/agents", tags=["数据查询"])
app.include_router(tasks.router, prefix="/api/tasks", tags=["任务管理"])


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "MuleRun Crawler API",
        "version": "1.0.0",
        "docs": "/docs"
    }

