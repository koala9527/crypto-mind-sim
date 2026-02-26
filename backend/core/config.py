"""
配置管理模块 - 使用 Pydantic Settings
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """应用配置"""

    # 数据库配置
    DATABASE_URL: str = "postgresql://neotrade:neotrade_pass@localhost:5432/neotrade"

    # 服务器配置
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # 交易配置
    INITIAL_BALANCE: float = 10000.0
    LIQUIDATION_THRESHOLD: float = 0.9  # 爆仓阈值 90%
    PRICE_UPDATE_INTERVAL: int = 60  # 价格更新间隔（秒）

    # 交易所配置
    EXCHANGE: str = "binance"
    TRADING_PAIR: str = "BTC/USDT"

    # 排行榜配置
    LEADERBOARD_TOP_N: int = 10

    # AI 配置 (只需要两个参数)
    AI_API_KEY: str = ""
    AI_BASE_URL: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
