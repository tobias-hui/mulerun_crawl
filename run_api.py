"""FastAPI 应用启动文件"""
import uvicorn
import os

if __name__ == "__main__":
    # 从环境变量读取端口，默认 8001
    port = int(os.getenv("PORT", 8001))
    
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=port,
        reload=True,  # 开发模式，生产环境应设为 False
        log_level="info"
    )

