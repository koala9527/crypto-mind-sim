"""???????"""

from datetime import datetime
import enum

import pytz
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum as SQLEnum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

DEFAULT_TRADING_FEE_RATE = 0.0004
DEFAULT_LIQUIDATION_THRESHOLD = 0.9
DEFAULT_INITIAL_BALANCE = 10000.0


def get_local_time() -> datetime:
    """????????????+8 ????"""
    tz = pytz.timezone("Asia/Shanghai")
    return datetime.now(tz).replace(tzinfo=None)


class TradeSide(str, enum.Enum):
    """???????"""

    LONG = "LONG"
    SHORT = "SHORT"
    BUY = "BUY"
    SELL = "SELL"


class TradeType(str, enum.Enum):
    """???????"""

    OPEN = "OPEN"
    CLOSE = "CLOSE"
    LIQUIDATION = "LIQUIDATION"
    HOLD = "HOLD"
    ERROR = "ERROR"


class User(Base):
    """????"""

    __tablename__ = "nt_users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password = Column(String(255), nullable=False)
    balance = Column(Float, default=DEFAULT_INITIAL_BALANCE, nullable=False)
    initial_balance = Column(Float, default=DEFAULT_INITIAL_BALANCE, nullable=False)
    trading_fee_rate = Column(Float, default=DEFAULT_TRADING_FEE_RATE, nullable=False)
    liquidation_threshold = Column(Float, default=DEFAULT_LIQUIDATION_THRESHOLD, nullable=False)
    ai_api_key = Column(String(200), nullable=True)
    ai_base_url = Column(String(200), nullable=True)
    ai_model = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=get_local_time, nullable=False)
    updated_at = Column(DateTime, default=get_local_time, onupdate=get_local_time, nullable=False)

    positions = relationship("Position", back_populates="user", cascade="all, delete-orphan")
    trades = relationship("Trade", back_populates="user", cascade="all, delete-orphan")
    ai_decisions = relationship("AIDecisionLog", back_populates="user", cascade="all, delete-orphan")
    ai_conversations = relationship("AIConversation", back_populates="user", cascade="all, delete-orphan")
    asset_history = relationship("AssetHistory", back_populates="user", cascade="all, delete-orphan")
    prompt_revisions = relationship("PromptRevisionHistory", back_populates="user", cascade="all, delete-orphan")


class Position(Base):
    """????"""

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
    created_at = Column(DateTime, default=get_local_time, nullable=False)
    closed_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="positions")


class Trade(Base):
    """??????"""

    __tablename__ = "nt_trades"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("nt_users.id"), nullable=False)
    position_id = Column(Integer, ForeignKey("nt_positions.id"), nullable=True)
    symbol = Column(String(20), nullable=False)
    side = Column(SQLEnum(TradeSide), nullable=False)
    position_side = Column(SQLEnum(TradeSide), nullable=True)
    price = Column(Float, nullable=False)
    quantity = Column(Float, nullable=False)
    leverage = Column(Integer, default=1, nullable=False)
    margin_used = Column(Float, nullable=True)
    notional_value = Column(Float, nullable=True)
    pnl = Column(Float, default=0.0, nullable=False)
    fee_paid = Column(Float, default=0.0, nullable=False)
    balance_before = Column(Float, nullable=True)
    balance_after = Column(Float, nullable=True)
    roi_pct = Column(Float, nullable=True)
    holding_seconds = Column(Integer, nullable=True)
    entry_price_snapshot = Column(Float, nullable=True)
    liquidation_price_snapshot = Column(Float, nullable=True)
    close_reason = Column(String(50), nullable=True)
    execution_source = Column(String(20), nullable=True)
    trade_type = Column(SQLEnum(TradeType), nullable=False)
    market_data = Column(Text, nullable=True)
    created_at = Column(DateTime, default=get_local_time, nullable=False)

    user = relationship("User", back_populates="trades")


class PromptConfig(Base):
    """AI ?????????"""

    __tablename__ = "nt_prompt_configs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("nt_users.id"), nullable=True)
    name = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=True)
    prompt_text = Column(Text, nullable=False)
    base_prompt_text = Column(Text, nullable=True)
    symbol = Column(String(20), nullable=False, default="BTC/USDT")
    ai_model = Column(String(50), nullable=False, default="claude-4.5-opus")
    execution_interval = Column(Integer, nullable=False, default=1, comment="????????")
    auto_optimize_prompt = Column(Boolean, default=False, nullable=False)
    prompt_optimization_interval = Column(Integer, nullable=False, default=1)
    prompt_optimization_include_hold = Column(Boolean, default=True, nullable=False)
    last_prompt_optimized_at = Column(DateTime, nullable=True)
    prompt_revision_count = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, default=False, nullable=False)
    last_executed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=get_local_time, nullable=False)
    updated_at = Column(DateTime, default=get_local_time, onupdate=get_local_time, nullable=False)

    user = relationship("User", foreign_keys=[user_id])
    prompt_revisions = relationship("PromptRevisionHistory", back_populates="strategy", cascade="all, delete-orphan")


class PromptRevisionHistory(Base):
    """?????????"""

    __tablename__ = "nt_prompt_revision_history"

    id = Column(Integer, primary_key=True, index=True)
    strategy_id = Column(Integer, ForeignKey("nt_prompt_configs.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("nt_users.id", ondelete="CASCADE"), nullable=False, index=True)
    revision_no = Column(Integer, nullable=False, default=1)
    source = Column(String(30), nullable=False)
    summary = Column(Text, nullable=True)
    previous_prompt_text = Column(Text, nullable=True)
    prompt_text = Column(Text, nullable=False)
    base_prompt_text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=get_local_time, nullable=False, index=True)

    strategy = relationship("PromptConfig", foreign_keys=[strategy_id], back_populates="prompt_revisions")
    user = relationship("User", foreign_keys=[user_id])


class MarketPrice(Base):
    """????????"""

    __tablename__ = "nt_market_prices"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    price = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=get_local_time, nullable=False, index=True)


class AssetHistory(Base):
    """???????????"""

    __tablename__ = "nt_asset_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("nt_users.id", ondelete="CASCADE"), nullable=False, index=True)
    total_assets = Column(Float, nullable=False)
    balance = Column(Float, nullable=False)
    position_value = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=get_local_time, nullable=False, index=True)

    user = relationship("User", back_populates="asset_history")


class AIDecisionLog(Base):
    """AI ??????"""

    __tablename__ = "nt_ai_decision_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("nt_users.id", ondelete="CASCADE"), nullable=True)
    prompt_name = Column(String(100), nullable=False)
    market_context = Column(Text, nullable=True)
    ai_reasoning = Column(Text, nullable=True)
    decision = Column(String(20), nullable=False)
    action_taken = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=get_local_time, nullable=False, index=True)

    user = relationship("User", back_populates="ai_decisions")


class AIConversation(Base):
    """AI ??????"""

    __tablename__ = "nt_ai_conversations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("nt_users.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=get_local_time, nullable=False, index=True)

    user = relationship("User", back_populates="ai_conversations")
