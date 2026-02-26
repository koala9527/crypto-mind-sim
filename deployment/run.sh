#!/bin/bash
# NeoTrade AI - Linux/Mac 启动脚本

echo "========================================"
echo "   NeoTrade AI - 加密货币模拟交易平台"
echo "========================================"
echo ""

# 检查 Python 是否安装
if ! command -v python3 &> /dev/null; then
    echo "[错误] 未检测到 Python3，请先安装 Python 3.8+"
    exit 1
fi

# 检查虚拟环境是否存在
if [ ! -d "venv" ]; then
    echo "[1/4] 创建虚拟环境..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "[错误] 虚拟环境创建失败"
        exit 1
    fi
fi

# 激活虚拟环境
echo "[2/4] 激活虚拟环境..."
source venv/bin/activate

# 安装依赖
echo "[3/4] 安装依赖包..."
pip install -r config/requirements.txt
if [ $? -ne 0 ]; then
    echo "[错误] 依赖安装失败"
    exit 1
fi

# 检查 .env 文件
if [ ! -f ".env" ]; then
    echo "[提示] 未找到 .env 文件，复制 .env.example..."
    cp config/.env.example .env
fi

# 初始化数据库和策略
if [ ! -f "neotrade.db" ]; then
    echo "[4/4] 初始化数据库和默认策略..."
    python -m backend.utils.init_prompts
fi

# 启动服务
echo ""
echo "========================================"
echo "   启动服务中..."
echo "   访问地址: http://localhost:8000"
echo "   API 文档: http://localhost:8000/docs"
echo "   按 Ctrl+C 停止服务"
echo "========================================"
echo ""

python main.py
