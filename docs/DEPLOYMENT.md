# 部署指南

## 本地开发

### 环境要求

- Python `3.11+`
- 推荐使用 `uv`
- 项目默认且仅支持 `SQLite`

### 快速启动

```bash
uv sync
uv run .\main.py
```

访问地址：

- 首页：`http://127.0.0.1:8010`
- API 文档：`http://127.0.0.1:8010/docs`

## 环境变量

复制 `config/.env.example` 到根目录 `.env`：

```bash
cp config/.env.example .env
```

当前推荐配置：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DATABASE_URL` | `sqlite:///./neotrade.db` | 本地 SQLite 数据库 |
| `HOST` | `127.0.0.1` | 监听地址 |
| `PORT` | `8010` | 监听端口 |
| `INITIAL_BALANCE` | `10000.0` | 初始模拟资金 |
| `LIQUIDATION_THRESHOLD` | `0.9` | 爆仓阈值 |
| `PRICE_UPDATE_INTERVAL` | `60` | 价格更新间隔（秒） |
| `TRADING_FEE_RATE` | `0.0004` | 手续费率 |
| `EXCHANGE` | `binance` | 行情来源交易所 |
| `TRADING_PAIR` | `BTC/USDT` | 默认交易对 |
| `LEADERBOARD_TOP_N` | `10` | 排行榜显示数量 |
| `SECRET_KEY` | `change-this-before-production` | 会话密钥 |

## AI 配置说明

AI 配置不通过 `.env` 提供，而是跟随账号保存：

- 注册账号时填写 `AI API Key`
- 可选填写 `AI Base URL`
- 可选填写 `AI 模型`
- 后续可在页面“设置”中修改

如果你使用 OpenAI 兼容接口，可以在注册或设置中填写类似：

- Base URL：`https://api.openai.com/v1`
- 模型：按你的服务商支持情况填写

## Docker

项目保留了 Docker 相关文件，但当前更推荐先使用本地 SQLite 方式完成演示和开源展示。

如需容器化运行，可自行基于当前 `.env` 配置扩展。

> 当前开源版本以 SQLite 学习场景为主，不再内置其他数据库配置。

## 生产建议

- 替换 `SECRET_KEY`
- 妥善备份 `neotrade.db` 并做好文件权限控制
- 给 AI Key 使用单独账号和最小权限
- 不要提交 `.env`
- 给 README 补上项目截图和免责声明
