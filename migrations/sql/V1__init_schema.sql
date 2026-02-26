-- ============================================================
-- V1: 初始化完整数据库结构（表前缀 nt_）
-- ============================================================

CREATE TYPE trade_side AS ENUM ('LONG', 'SHORT', 'BUY', 'SELL');
CREATE TYPE trade_type AS ENUM ('OPEN', 'CLOSE', 'LIQUIDATION');

CREATE TABLE nt_users (
    id               SERIAL PRIMARY KEY,
    username         VARCHAR(50)  NOT NULL UNIQUE,
    password         VARCHAR(100) NOT NULL,
    balance          FLOAT        NOT NULL DEFAULT 10000.0,
    initial_balance  FLOAT        NOT NULL DEFAULT 10000.0,
    ai_api_key       VARCHAR(200),
    ai_base_url      VARCHAR(200),
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_nt_users_username ON nt_users(username);

CREATE TABLE nt_positions (
    id                SERIAL PRIMARY KEY,
    user_id           INTEGER      NOT NULL REFERENCES nt_users(id) ON DELETE CASCADE,
    symbol            VARCHAR(20)  NOT NULL,
    side              trade_side   NOT NULL,
    entry_price       FLOAT        NOT NULL,
    quantity          FLOAT        NOT NULL,
    leverage          INTEGER      NOT NULL DEFAULT 1,
    margin            FLOAT        NOT NULL,
    unrealized_pnl    FLOAT        NOT NULL DEFAULT 0.0,
    is_open           BOOLEAN      NOT NULL DEFAULT TRUE,
    liquidation_price FLOAT,
    created_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    closed_at         TIMESTAMPTZ
);
CREATE INDEX idx_nt_positions_user_id ON nt_positions(user_id);
CREATE INDEX idx_nt_positions_is_open  ON nt_positions(is_open);

CREATE TABLE nt_trades (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER     NOT NULL REFERENCES nt_users(id) ON DELETE CASCADE,
    symbol      VARCHAR(20) NOT NULL,
    side        trade_side  NOT NULL,
    price       FLOAT       NOT NULL,
    quantity    FLOAT       NOT NULL,
    leverage    INTEGER     NOT NULL DEFAULT 1,
    pnl         FLOAT       NOT NULL DEFAULT 0.0,
    trade_type  trade_type  NOT NULL,
    market_data TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_nt_trades_user_id    ON nt_trades(user_id);
CREATE INDEX idx_nt_trades_created_at ON nt_trades(created_at DESC);

CREATE TABLE nt_prompt_configs (
    id                 SERIAL PRIMARY KEY,
    user_id            INTEGER      REFERENCES nt_users(id) ON DELETE CASCADE,
    name               VARCHAR(100) NOT NULL,
    description        TEXT,
    prompt_text        TEXT         NOT NULL,
    symbol             VARCHAR(20)  NOT NULL DEFAULT 'BTC/USDT',
    ai_model           VARCHAR(50)  NOT NULL DEFAULT 'claude-4.5-opus',
    execution_interval INTEGER      NOT NULL DEFAULT 60,
    is_active          BOOLEAN      NOT NULL DEFAULT FALSE,
    last_executed_at   TIMESTAMPTZ,
    created_at         TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at         TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_nt_prompt_configs_name    ON nt_prompt_configs(name);
CREATE INDEX idx_nt_prompt_configs_user_id ON nt_prompt_configs(user_id);

CREATE TABLE nt_market_prices (
    id        SERIAL PRIMARY KEY,
    symbol    VARCHAR(20) NOT NULL,
    price     FLOAT       NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_nt_market_prices_symbol    ON nt_market_prices(symbol);
CREATE INDEX idx_nt_market_prices_timestamp ON nt_market_prices(timestamp DESC);

CREATE TABLE nt_asset_history (
    id             SERIAL PRIMARY KEY,
    user_id        INTEGER     NOT NULL REFERENCES nt_users(id) ON DELETE CASCADE,
    total_assets   FLOAT       NOT NULL,
    balance        FLOAT       NOT NULL,
    position_value FLOAT       NOT NULL,
    timestamp      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_nt_asset_history_user_time ON nt_asset_history(user_id, timestamp DESC);

CREATE TABLE nt_ai_decision_logs (
    id             SERIAL PRIMARY KEY,
    user_id        INTEGER      REFERENCES nt_users(id) ON DELETE CASCADE,
    prompt_name    VARCHAR(100) NOT NULL,
    market_context TEXT,
    ai_reasoning   TEXT,
    decision       VARCHAR(20)  NOT NULL,
    action_taken   BOOLEAN      NOT NULL DEFAULT FALSE,
    created_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_nt_ai_decision_logs_user_id    ON nt_ai_decision_logs(user_id);
CREATE INDEX idx_nt_ai_decision_logs_created_at ON nt_ai_decision_logs(created_at DESC);

CREATE TABLE nt_ai_conversations (
    id         SERIAL PRIMARY KEY,
    user_id    INTEGER     NOT NULL REFERENCES nt_users(id) ON DELETE CASCADE,
    role       VARCHAR(20) NOT NULL,
    content    TEXT        NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_nt_ai_conversations_user_id    ON nt_ai_conversations(user_id);
CREATE INDEX idx_nt_ai_conversations_created_at ON nt_ai_conversations(created_at DESC);
