# 开发日志

记录项目开发过程中的重要变更和修复。

---

## 架构变更

### 项目结构重组
将扁平结构重组为模块化目录：
- `backend/core/` — 核心模块（main, config, database, models）
- `backend/api/` — API 路由
- `backend/services/` — 服务层（AI 服务、调度器）
- `backend/engine/` — 交易引擎
- `backend/utils/` — 工具脚本
- `frontend/static/js/` — 前端 JS 模块化（从 inline 迁移到独立文件）
- `deployment/` — Docker 和部署脚本
- `config/` — 配置文件模板

### AI 配置迁移
1. 初始：服务端 `.env` 配置 5 个 AI 变量
2. 简化：缩减为 2 个变量（`AI_API_KEY` + `AI_BASE_URL`）
3. 客户端化：迁移到浏览器 localStorage（每用户独立 Key）
4. 最终方案：localStorage + 服务器数据库双重同步

### 数据库演进
- SQLite → PostgreSQL（psycopg3）
- 添加 User 表 `password` 字段（注册/登录）
- 添加 User 表 `ai_api_key`、`ai_base_url` 字段
- 添加 PromptConfig 表 `leverage`、`user_id` 等字段

---

## 功能实现记录

### 策略预设系统
- 6 种预设模板（激进、稳健、网格、趋势、突破、均值回归）
- 预设仅提供提示词，交易参数由用户独立选择
- 路由顺序修复：`/presets` 必须在 `/{strategy_id}` 之前

### 策略执行引擎
- 从「仅记录决策」升级为「实际执行交易」
- `execute_open_position()` — 计算保证金、创建持仓
- `execute_close_positions()` — 计算盈亏、关闭持仓

### 交易详情功能
- 点击交易记录弹出详情模态框
- 显示 AI 决策分析（通过时间戳匹配关联）
- 24 小时价格走势图 + 交易价格标注

### 用户删除功能
- `DELETE /api/users/{user_id}` 级联删除所有关联数据
- 前端三重确认流程

### 国际化 (i18n)
- `i18n.js` 实现中英文切换
- `t(key)` 翻译函数 + `data-i18n` 属性自动翻译
- 语言偏好保存到 localStorage

---

## 已清理的文件

- `components.js` — 已废弃，功能合并到其他模块
- `i18n-apply.js` — 已废弃，功能合并到 `i18n.js`
- `ai_service.py.old` — 旧版备份
- `static/*.old`, `*.bak`, `*backup.html` — 临时备份文件
