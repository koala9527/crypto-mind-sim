-- PostgreSQL 初始化脚本
-- 创建所有表和索引

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(100) NOT NULL,
    balance DOUBLE PRECISION NOT NULL DEFAULT 10000.0,
    initial_balance DOUBLE PRECISION NOT NULL DEFAULT 10000.0,
    ai_api_key VARCHAR(200),
    ai_base_url VARCHAR(200),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS positions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL,
    entry_price DOUBLE PRECISION NOT NULL,
    quantity DOUBLE PRECISION NOT NULL,
    leverage INTEGER NOT NULL DEFAULT 1,
    margin DOUBLE PRECISION NOT NULL,
    unrealized_pnl DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    is_open BOOLEAN NOT NULL DEFAULT TRUE,
    liquidation_price DOUBLE PRECISION,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    closed_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS trades (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL,
    price DOUBLE PRECISION NOT NULL,
    quantity DOUBLE PRECISION NOT NULL,
    leverage INTEGER NOT NULL DEFAULT 1,
    pnl DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    trade_type VARCHAR(20) NOT NULL,
    market_data TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS prompt_configs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    prompt_text TEXT NOT NULL,
    symbol VARCHAR(20) NOT NULL DEFAULT 'BTC/USDT',
    ai_model VARCHAR(50) NOT NULL DEFAULT 'claude-4.5-opus',
    execution_interval INTEGER NOT NULL DEFAULT 60,
    is_active BOOLEAN NOT NULL DEFAULT FALSE,
    last_executed_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS market_prices (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    price DOUBLE PRECISION NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ai_decision_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    prompt_name VARCHAR(100) NOT NULL,
    market_context TEXT,
    ai_reasoning TEXT,
    decision VARCHAR(20) NOT NULL,
    action_taken BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ai_conversations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- 索引
CREATE INDEX IF NOT EXISTS ix_users_id ON users(id);
CREATE INDEX IF NOT EXISTS ix_users_username ON users(username);
CREATE INDEX IF NOT EXISTS ix_positions_id ON positions(id);
CREATE INDEX IF NOT EXISTS ix_trades_id ON trades(id);
CREATE INDEX IF NOT EXISTS ix_prompt_configs_id ON prompt_configs(id);
CREATE INDEX IF NOT EXISTS ix_prompt_configs_name ON prompt_configs(name);
CREATE INDEX IF NOT EXISTS ix_market_prices_id ON market_prices(id);
CREATE INDEX IF NOT EXISTS ix_market_prices_symbol ON market_prices(symbol);
CREATE INDEX IF NOT EXISTS ix_market_prices_timestamp ON market_prices(timestamp);
CREATE INDEX IF NOT EXISTS ix_ai_decision_logs_id ON ai_decision_logs(id);
CREATE INDEX IF NOT EXISTS ix_ai_decision_logs_created_at ON ai_decision_logs(created_at);
CREATE INDEX IF NOT EXISTS ix_ai_conversations_id ON ai_conversations(id);
CREATE INDEX IF NOT EXISTS ix_ai_conversations_created_at ON ai_conversations(created_at);
