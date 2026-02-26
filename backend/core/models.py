"""
数据库模型定义
"""
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
    Enum as SQLEnum,
)
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime
import enum

Base = declarative_base()


class TradeSide(str, enum.Enum):
    """交易方向枚举"""

    LONG = "LONG"
    SHORT = "SHORT"
    BUY = "BUY"
    SELL = "SELL"


class TradeType(str, enum.Enum):
    """交易类型枚举"""

    OPEN = "OPEN"  # 开仓
    CLOSE = "CLOSE"  # 平仓
    LIQUIDATION = "LIQUIDATION"  # 爆仓
    HOLD = "HOLD"  # 持有（AI决策不操作）
    ERROR = "ERROR"  # 执行异常


class User(Base):
    """用户表"""

    __tablename__ = "nt_users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password = Column(String(100), nullable=False)
    balance = Column(Float, default=10000.0, nullable=False)
    initial_balance = Column(Float, default=10000.0, nullable=False)
    ai_api_key = Column(String(200), nullable=True)
    ai_base_url = Column(String(200), nullable=True)
    ai_model = Column(String(100), nullable=True, default="claude-4.5-opus")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    positions = relationship("Position", back_populates="user", cascade="all, delete-orphan")
    trades = relationship("Trade", back_populates="user", cascade="all, delete-orphan")
    ai_decisions = relationship("AIDecisionLog", back_populates="user", cascade="all, delete-orphan")
    ai_conversations = relationship("AIConversation", back_populates="user", cascade="all, delete-orphan")
    asset_history = relationship("AssetHistory", back_populates="user", cascade="all, delete-orphan")


class Position(Base):
    """持仓表"""

    __tablename__ = "nt_positions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("nt_users.id"), nullable=False)
    symbol = Column(String(20), nullable=False)
    side = Column(SQLEnum(TradeSide), nullable=False)
    entry_price = Column(Float, nullable=False)
    quantity = Column(Float, nullable=False)
    leverage = Column(Integer, default=1, nullable=False)
    margin = Column(Float, nullable=False)
    unrealized_pnl = Column(Float, default=0.0, nullable=False)
    is_open = Column(Boolean, default=True, nullable=False)
    liquidation_price = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    closed_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="positions")


class Trade(Base):
    """交易历史表"""

    __tablename__ = "nt_trades"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("nt_users.id"), nullable=False)
    symbol = Column(String(20), nullable=False)
    side = Column(SQLEnum(TradeSide), nullable=False)
    price = Column(Float, nullable=False)
    quantity = Column(Float, nullable=False)
    leverage = Column(Integer, default=1, nullable=False)
    pnl = Column(Float, default=0.0, nullable=False)
    trade_type = Column(SQLEnum(TradeType), nullable=False)
    market_data = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="trades")


class PromptConfig(Base):
    """AI 策略提示词配置表"""

    __tablename__ = "nt_prompt_configs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("nt_users.id"), nullable=True)
    name = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=True)
    prompt_text = Column(Text, nullable=False)
    symbol = Column(String(20), nullable=False, default="BTC/USDT")
    ai_model = Column(String(50), nullable=False, default="claude-4.5-opus")
    execution_interval = Column(Integer, nullable=False, default=60)
    is_active = Column(Boolean, default=False, nullable=False)
    last_executed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    user = relationship("User", foreign_keys=[user_id])


class MarketPrice(Base):
    """市场价格历史表"""

    __tablename__ = "nt_market_prices"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    price = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class AssetHistory(Base):
    """用户总资产历史快照表"""

    __tablename__ = "nt_asset_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("nt_users.id", ondelete="CASCADE"), nullable=False, index=True)
    total_assets = Column(Float, nullable=False)
    balance = Column(Float, nullable=False)
    position_value = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    user = relationship("User", back_populates="asset_history")


class AIDecisionLog(Base):
    """AI 决策日志表"""

    __tablename__ = "nt_ai_decision_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("nt_users.id", ondelete="CASCADE"), nullable=True)
    prompt_name = Column(String(100), nullable=False)
    market_context = Column(Text, nullable=True)
    ai_reasoning = Column(Text, nullable=True)
    decision = Column(String(20), nullable=False)
    action_taken = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    user = relationship("User", back_populates="ai_decisions")


class AIConversation(Base):
    """AI 对话历史表"""

    __tablename__ = "nt_ai_conversations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("nt_users.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    user = relationship("User", back_populates="ai_conversations")
