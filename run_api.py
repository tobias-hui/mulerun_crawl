"""FastAPI 应用启动文件"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # 开发模式，生产环境应设为 False
        log_level="info"
    )

