@echo off
echo ============================================
echo CryptoMindSim - 启动脚本 (Windows)
echo ============================================

REM 检查虚拟环境
if not exist "venv\" (
    echo [错误] 虚拟环境不存在，请先运行安装脚本
    pause
    exit /b 1
)

REM 激活虚拟环境
echo [1/2] 激活虚拟环境...
call venv\Scripts\activate.bat

REM 启动应用
echo [2/2] 启动应用...
echo.
echo ============================================
echo 应用已启动！
echo 访问地址: http://localhost:8000
echo 按 Ctrl+C 停止服务
echo ============================================
echo.

REM 启动 uvicorn
python -m uvicorn backend.core.main:app --host 0.0.0.0 --port 8000 --reload

pause
