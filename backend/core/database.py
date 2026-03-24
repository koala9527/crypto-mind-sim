"""数据库连接和会话管理。"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from backend.core.config import settings
from backend.core.models import (
    Base,
    DEFAULT_INITIAL_BALANCE,
    DEFAULT_LIQUIDATION_THRESHOLD,
    DEFAULT_TRADING_FEE_RATE,
)


db_url = settings.DATABASE_URL

if not db_url.lower().startswith("sqlite"):
    raise RuntimeError(
        "CryptoMindSim 当前仅支持 SQLite，请将 DATABASE_URL 设置为 sqlite:///./neotrade.db。"
    )

engine_kwargs = {
    "echo": False,
    "pool_pre_ping": True,
    "connect_args": {"check_same_thread": False},
}

engine = create_engine(db_url, **engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _ensure_prompt_config_columns():
    """为 SQLite 旧库补齐策略优化相关字段。"""
    with engine.begin() as conn:
        table_exists = conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='nt_prompt_configs'")
        ).first()
        if not table_exists:
            return

        existing_columns = {
            row[1]
            for row in conn.execute(text("PRAGMA table_info(nt_prompt_configs)"))
        }

        migrations = {
            "base_prompt_text": "ALTER TABLE nt_prompt_configs ADD COLUMN base_prompt_text TEXT",
            "auto_optimize_prompt": "ALTER TABLE nt_prompt_configs ADD COLUMN auto_optimize_prompt BOOLEAN NOT NULL DEFAULT 0",
            "prompt_optimization_interval": "ALTER TABLE nt_prompt_configs ADD COLUMN prompt_optimization_interval INTEGER NOT NULL DEFAULT 1",
            "prompt_optimization_include_hold": "ALTER TABLE nt_prompt_configs ADD COLUMN prompt_optimization_include_hold BOOLEAN NOT NULL DEFAULT 1",
            "last_prompt_optimized_at": "ALTER TABLE nt_prompt_configs ADD COLUMN last_prompt_optimized_at DATETIME",
            "prompt_revision_count": "ALTER TABLE nt_prompt_configs ADD COLUMN prompt_revision_count INTEGER NOT NULL DEFAULT 0",
        }

        for column_name, ddl in migrations.items():
            if column_name not in existing_columns:
                conn.execute(text(ddl))

        conn.execute(
            text(
                """
                UPDATE nt_prompt_configs
                SET base_prompt_text = prompt_text
                WHERE base_prompt_text IS NULL OR TRIM(base_prompt_text) = ''
                """
            )
        )
        conn.execute(
            text(
                """
                UPDATE nt_prompt_configs
                SET prompt_optimization_interval = 1
                WHERE prompt_optimization_interval IS NULL OR prompt_optimization_interval < 1
                """
            )
        )
        conn.execute(
            text(
                """
                UPDATE nt_prompt_configs
                SET prompt_revision_count = 0
                WHERE prompt_revision_count IS NULL
                """
            )
        )


def _ensure_user_config_columns():
    """为 SQLite 旧库补齐用户级交易配置字段。"""
    with engine.begin() as conn:
        table_exists = conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='nt_users'")
        ).first()
        if not table_exists:
            return

        existing_columns = {
            row[1]
            for row in conn.execute(text("PRAGMA table_info(nt_users)"))
        }

        migrations = {
            "trading_fee_rate": f"ALTER TABLE nt_users ADD COLUMN trading_fee_rate FLOAT NOT NULL DEFAULT {DEFAULT_TRADING_FEE_RATE}",
            "liquidation_threshold": f"ALTER TABLE nt_users ADD COLUMN liquidation_threshold FLOAT NOT NULL DEFAULT {DEFAULT_LIQUIDATION_THRESHOLD}",
        }

        for column_name, ddl in migrations.items():
            if column_name not in existing_columns:
                conn.execute(text(ddl))

        conn.execute(
            text(
                f"""
                UPDATE nt_users
                SET trading_fee_rate = {DEFAULT_TRADING_FEE_RATE}
                WHERE trading_fee_rate IS NULL OR trading_fee_rate < 0
                """
            )
        )
        conn.execute(
            text(
                f"""
                UPDATE nt_users
                SET liquidation_threshold = {DEFAULT_LIQUIDATION_THRESHOLD}
                WHERE liquidation_threshold IS NULL OR liquidation_threshold <= 0
                """
            )
        )
        conn.execute(
            text(
                f"""
                UPDATE nt_users
                SET initial_balance = {DEFAULT_INITIAL_BALANCE}
                WHERE initial_balance IS NULL OR initial_balance <= 0
                """
            )
        )


def init_db():
    """初始化数据库并创建表结构。"""
    Base.metadata.create_all(bind=engine)
    _ensure_user_config_columns()
    _ensure_prompt_config_columns()


def get_db():
    """依赖注入：获取数据库会话。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
