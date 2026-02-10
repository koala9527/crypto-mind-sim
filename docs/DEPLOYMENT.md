# 部署指南

## 本地开发

### 环境要求

- Python 3.11+（推荐 3.13）
- PostgreSQL 15+
- uv 包管理器（推荐）或 pip

### 快速启动

```bash
# 使用 uv（推荐）
uv run python main.py

# 或使用启动脚本
deployment\run.bat         # Windows
deployment\start.bat       # Windows 快速启动
./deployment/run.sh        # Linux/Mac
```

### 手动安装

```bash
# 创建虚拟环境并安装依赖
uv sync

# 或使用 pip
python -m venv .venv
.venv\Scripts\activate     # Windows
pip install -r config/requirements.txt

# 启动服务
python main.py
```

访问：**http://localhost:8000**

---

## 环境变量

复制 `config/.env.example` 为项目根目录 `.env`：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| DATABASE_URL | postgresql://neotrade:neotrade_pass@localhost:5432/neotrade | 数据库连接 |
| HOST | 0.0.0.0 | 监听地址 |
| PORT | 8000 | 监听端口 |
| INITIAL_BALANCE | 10000.0 | 用户初始资金 |
| LIQUIDATION_THRESHOLD | 0.9 | 爆仓阈值（90%） |
| PRICE_UPDATE_INTERVAL | 60 | 价格更新间隔（秒） |
| EXCHANGE | binance | 交易所 |
| TRADING_PAIR | BTC/USDT | 默认交易对 |
| AI_API_KEY | - | AI 服务 API Key |
| AI_BASE_URL | https://api.hodlai.fun/v1 | AI 服务地址 |

---

## Docker 部署

### 使用 docker-compose（推荐）

```bash
cd deployment

# 仅启动应用（需要外部数据库）
docker-compose up -d

# 启动应用 + PostgreSQL
docker-compose --profile with-db up -d
```

### 手动 Docker 构建

```bash
# 从项目根目录构建
docker build -f deployment/Dockerfile -t neotrade-ai .

# 运行
docker run -d -p 8000:8000 \
  -e DATABASE_URL=postgresql://user:pass@host:5432/neotrade \
  --name neotrade neotrade-ai
```

### 生产部署

```bash
cd deployment
docker-compose -f docker-compose.prod.yml up -d
```

---

## 数据库

### PostgreSQL 配置

默认连接：`postgresql://neotrade:neotrade_pass@localhost:5432/neotrade`

`database.py` 自动将 `postgresql://` 转换为 `postgresql+psycopg://` 以适配 SQLAlchemy + psycopg3。

### 数据库初始化

应用启动时自动调用 `init_db()` 创建表结构。也可使用 `deployment/init.sql` 手动初始化。

### 数据库重置

```bash
# 使用脚本
python -m backend.utils.reset_db

# Windows 批处理
deployment\clear_and_reset.bat
```

---

## 数据备份与恢复

```bash
# 备份
docker exec neotrade-db pg_dump -U neotrade neotrade > backup.sql

# 恢复
docker exec -i neotrade-db psql -U neotrade neotrade < backup.sql
```

---

## 健康检查

```bash
curl http://localhost:8000/api/stats
```

Docker 容器内置健康检查，每 30 秒自动检测。

---

## Nginx 反向代理（可选）

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```
