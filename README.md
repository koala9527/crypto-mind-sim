# NeoTrade AI

加密货币 AI 模拟交易平台 — 基于 FastAPI + PostgreSQL + CCXT

## 核心特性

- **模拟交易**：每位用户初始 10,000 USDT，支持 1-20 倍杠杆做多/做空
- **实时行情**：通过 CCXT 获取 10 种主流加密货币实时价格
- **AI 策略**：接入 8 种大语言模型，6 种预设策略模板，自动化交易执行
- **AI 对话**：与 AI 助手实时对话，获取市场分析和交易建议
- **决策日志**：完整记录 AI 推理过程和执行结果
- **排行榜**：实时资产排名竞技
- **爆仓机制**：保证金亏损率 > 90% 自动强制平仓
- **国际化**：中英文切换

## 快速启动

```bash
# 安装依赖
uv sync

# 配置环境变量
cp config/.env.example .env
# 编辑 .env 设置数据库连接和 AI API Key

# 启动
uv run python main.py
```

访问 **http://localhost:8000** | API 文档 **http://localhost:8000/docs**

## 项目结构

```
├── main.py                  # 入口文件
├── backend/
│   ├── core/                # 核心：main, config, database, models
│   ├── api/                 # API 路由：ai_routes, strategy_routes, user_routes
│   ├── services/            # 服务：ai_service, ai_scheduler
│   ├── engine/              # 交易引擎：engine, strategy_executor
│   └── utils/               # 工具：init_prompts, reset_db
├── frontend/static/         # 前端：index.html + css/ + js/
├── deployment/              # Docker、启动脚本
├── config/                  # .env.example, requirements.txt
└── docs/                    # 文档
```

## 技术栈

**后端**：FastAPI · SQLAlchemy · PostgreSQL (psycopg3) · CCXT · APScheduler · httpx

**前端**：Tailwind CSS · Chart.js · Vanilla JavaScript

## 文档

- [AI 功能指南](docs/AI_GUIDE.md) — 模型配置、API 接口、决策系统
- [策略管理指南](docs/STRATEGY_GUIDE.md) — 预设模板、执行机制、最佳实践
- [部署指南](docs/DEPLOYMENT.md) — 本地开发、Docker、数据库、环境变量
- [开发日志](docs/CHANGELOG.md) — 架构变更、功能实现记录

## 许可证

MIT License
