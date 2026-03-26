# 部署指南

## 本地运行

### 环境要求

- Python `3.11+`
- 推荐使用 `uv`
- 默认使用 `SQLite`

### 启动步骤

```bash
uv sync
uv run .\main.py
```

访问地址：

- 首页：`http://127.0.0.1:8010`
- API 文档：`http://127.0.0.1:8010/docs`

## 环境变量

复制示例文件：

```bash
cp config/.env.example .env
```

通常只需要确认以下配置：

- `DATABASE_URL`
- `HOST`
- `PORT`
- `SECRET_KEY`

## 用户级配置

以下参数在页面“设置”中按用户保存，不需要写入 `.env`：

- AI API Key
- AI Base URL
- AI 模型
- 手续费率
- 爆仓阈值
- 初始模拟资金

## 开源建议

- 不要提交 `.env`
- 不要提交数据库文件和本地缓存文件
- 不要提交真实 AI Key 或生产配置
- 发布前至少手动检查一次注册、策略编辑、开平仓和设置保存流程
