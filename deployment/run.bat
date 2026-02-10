@echo off
REM NeoTrade AI - Windows 启动脚本

echo ========================================
echo    NeoTrade AI - 加密货币模拟交易平台
echo ========================================
echo.

REM 检查 Python 是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Python，请先安装 Python 3.8+
    pause
    exit /b 1
)

REM 检查虚拟环境是否存在
if not exist "venv\" (
    echo [1/4] 创建虚拟环境...
    python -m venv venv
    if errorlevel 1 (
        echo [错误] 虚拟环境创建失败
        pause
        exit /b 1
    )
)

REM 激活虚拟环境
echo [2/4] 激活虚拟环境...
call venv\Scripts\activate.bat

REM 安装依赖
echo [3/4] 安装依赖包...
pip install -r config\requirements.txt
if errorlevel 1 (
    echo [错误] 依赖安装失败
    pause
    exit /b 1
)

REM 检查 .env 文件
if not exist ".env" (
    echo [提示] 未找到 .env 文件，复制 .env.example...
    copy config\.env.example .env
)

REM 初始化数据库和策略
if not exist "neotrade.db" (
    echo [4/4] 初始化数据库和默认策略...
    python -m backend.utils.init_prompts
)

REM 启动服务
echo.
echo ========================================
echo    启动服务中...
echo    访问地址: http://localhost:8000
echo    API 文档: http://localhost:8000/docs
echo    按 Ctrl+C 停止服务
echo ========================================
echo.

python main.py

pause
