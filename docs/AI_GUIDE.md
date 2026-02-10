# AI 功能指南

## 概述

NeoTrade AI 通过 HodlAI 中转服务（OpenAI 兼容接口）接入多种大语言模型，实现智能交易分析和自动化策略执行。

---

## 支持的 AI 模型

| 模型 | 提供商 |
|------|--------|
| GPT-5.2 | OpenAI |
| o3 Pro | OpenAI |
| Claude 4.5 Opus | Anthropic |
| Gemini 3 Pro | Google |
| DeepSeek R1 | DeepSeek |
| Grok 4 | xAI |
| Kimi K2 | Moonshot |
| Qwen3 Max | Alibaba |

默认模型：`claude-4.5-opus`，温度 `0.7`，最大 token `2000`。

---

## 配置方式

### API Key 存储（双重同步机制）

AI 配置采用 **浏览器 localStorage + 服务器数据库** 双重存储：

- **前端**：`settings.js` 通过 `getAIConfig()` / `saveAIConfig()` 管理 localStorage
- **后端**：User 表的 `ai_api_key`、`ai_base_url` 字段
- **同步时机**：登录时自动同步、保存设置时同步、页面刷新时同步

#### 同步 API

| 方法 | 路径 | 说明 |
|------|------|------|
| PUT | `/api/users/{user_id}/ai-config` | 保存 AI 配置到服务器 |
| GET | `/api/users/{user_id}/ai-config` | 从服务器获取 AI 配置 |
| DELETE | `/api/users/{user_id}/ai-config` | 清除服务器端 AI 配置 |

### 环境变量（服务端默认值）

```bash
AI_API_KEY=your_api_key_here
AI_BASE_URL=https://api.hodlai.fun/v1
```

---

## AI API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/ai/models` | 获取支持的模型列表 |
| POST | `/api/ai/analyze` | AI 市场分析 |
| POST | `/api/ai/advice` | AI 交易建议 |

### AI 服务架构

- `backend/services/ai_service.py` — AI 服务核心，使用 `httpx` 调用 OpenAI 兼容 API
- `backend/api/ai_routes.py` — AI 相关路由
- `backend/services/ai_scheduler.py` — 定时任务调度

---

## AI 对话系统

用户可通过 Web 界面与 AI 助手实时对话：

- 对话历史保存到 `AIConversation` 表，刷新不丢失
- 支持快捷咨询按钮（市场趋势、开仓建议、止损止盈、交易分析）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/users/{user_id}/conversations` | 获取对话历史 |
| POST | `/api/users/{user_id}/conversations` | 发送消息给 AI |

---

## AI 决策日志

所有 AI 决策过程自动记录到 `AIDecisionLog` 表：

- 策略名称、市场上下文、AI 推理过程
- 决策结果（BUY/SELL/HOLD）、是否实际执行

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/users/{user_id}/ai-decisions` | 获取 AI 决策日志 |

---

## 策略自动执行

策略执行器 `backend/engine/strategy_executor.py` 负责自动化交易：

1. 读取用户激活的策略和 AI 配置（从 User 表获取 `ai_api_key`）
2. 获取当前市场数据，构建上下文
3. 调用 AI 模型分析，获取 JSON 格式决策
4. 根据决策自动执行开仓/平仓操作

### AI 决策 JSON 格式

```json
{
  "action": "open",
  "direction": "long",
  "quantity": 0.1,
  "leverage": 5,
  "reasoning": "MACD 金叉确认，RSI 处于强势区间..."
}
```

`action` 可选值：`open`（开仓）、`close`（平仓）、`hold`（观望）
