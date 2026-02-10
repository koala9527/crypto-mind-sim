"""
NeoTrade AI 主入口文件
"""
import uvicorn
from backend.core.main import app
from backend.core.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "backend.core.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True  # 开发模式下启用热重载
    )
