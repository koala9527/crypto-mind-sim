"""配置管理模块。"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置"""

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
    )

    # 数据库配置
    DATABASE_URL: str = "sqlite:///./neotrade.db"

    # 服务配置
    HOST: str = "127.0.0.1"
    PORT: int = 8010

    # 交易配置
    PRICE_UPDATE_INTERVAL: int = 60

    # 交易所配置
    EXCHANGE: str = "binance"
    TRADING_PAIR: str = "BTC/USDT"

    # 排行榜配置
    LEADERBOARD_TOP_N: int = 10

    # 会话配置
    SECRET_KEY: str = "change-this-before-production"
    SESSION_COOKIE_NAME: str = "neotrade_session"
    SESSION_MAX_AGE: int = 60 * 60 * 24 * 7
    DISABLE_SCHEDULER: bool = False

    # 时区配置
    TIMEZONE: str = "Asia/Shanghai"


settings = Settings()
