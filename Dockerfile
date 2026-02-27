# 使用轻量级 Python 基础镜像（使用阿里云镜像加速）
FROM registry.cn-hangzhou.aliyuncs.com/library/python:3.11-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 安装系统依赖（含 libpq-dev for psycopg2）
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY config/requirements.txt .

# 安装 Python 依赖（使用阿里云 pip 镜像加速）
RUN pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple/ -r requirements.txt

# 复制项目文件
COPY . .

# 创建数据目录
RUN mkdir -p /app/data

# 暴露端口
EXPOSE 8000

# 健康检查（使用 curl 代替 requests）
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/stats || exit 1

# 启动应用
CMD ["uvicorn", "backend.core.main:app", "--host", "0.0.0.0", "--port", "8000"]
