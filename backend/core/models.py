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


class User(Base):
    """用户表"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password = Column(String(100), nullable=False)  # 密码（简单存储，实际应加密）
    balance = Column(Float, default=10000.0, nullable=False)  # 当前余额
    initial_balance = Column(Float, default=10000.0, nullable=False)  # 初始资金
    # AI 配置（存储在用户表中，但实际从前端传入）
    ai_api_key = Column(String(200), nullable=True)  # API Key（加密存储，暂时可选）
    ai_base_url = Column(String(200), nullable=True)  # Base URL（可选）
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # 关系（级联删除）
    positions = relationship("Position", back_populates="user", cascade="all, delete-orphan")
    trades = relationship("Trade", back_populates="user", cascade="all, delete-orphan")
    ai_decisions = relationship("AIDecisionLog", back_populates="user", cascade="all, delete-orphan")
    ai_conversations = relationship("AIConversation", back_populates="user", cascade="all, delete-orphan")


class Position(Base):
    """持仓表"""

    __tablename__ = "positions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    symbol = Column(String(20), nullable=False)  # 交易对，如 BTC/USDT
    side = Column(SQLEnum(TradeSide), nullable=False)  # LONG/SHORT
    entry_price = Column(Float, nullable=False)  # 开仓价格
    quantity = Column(Float, nullable=False)  # 持仓数量
    leverage = Column(Integer, default=1, nullable=False)  # 杠杆倍数
    margin = Column(Float, nullable=False)  # 保证金
    unrealized_pnl = Column(Float, default=0.0, nullable=False)  # 未实现盈亏
    is_open = Column(Boolean, default=True, nullable=False)  # 是否开仓中
    liquidation_price = Column(Float, nullable=True)  # 爆仓价格（预留）
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    closed_at = Column(DateTime, nullable=True)

    # 关系
    user = relationship("User", back_populates="positions")


class Trade(Base):
    """交易历史表"""

    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    symbol = Column(String(20), nullable=False)
    side = Column(SQLEnum(TradeSide), nullable=False)  # BUY/SELL
    price = Column(Float, nullable=False)  # 成交价格
    quantity = Column(Float, nullable=False)  # 数量
    leverage = Column(Integer, default=1, nullable=False)  # 杠杆
    pnl = Column(Float, default=0.0, nullable=False)  # 已实现盈亏
    trade_type = Column(SQLEnum(TradeType), nullable=False)  # OPEN/CLOSE/LIQUIDATION
    # 市场数据快照
    market_data = Column(Text, nullable=True)  # JSON格式存储市场数据（价格、指标等）
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # 关系
    user = relationship("User", back_populates="trades")


class PromptConfig(Base):
    """AI 策略提示词配置表"""

    __tablename__ = "prompt_configs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # 所属用户（可为空表示全局策略）
    name = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=True)
    prompt_text = Column(Text, nullable=False)
    symbol = Column(String(20), nullable=False, default="BTC/USDT")  # 交易对
    ai_model = Column(String(50), nullable=False, default="claude-4.5-opus")  # AI 模型
    execution_interval = Column(Integer, nullable=False, default=60)  # 执行频率（秒）
    is_active = Column(Boolean, default=False, nullable=False)  # 是否激活
    last_executed_at = Column(DateTime, nullable=True)  # 上次执行时间
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # 关系
    user = relationship("User", foreign_keys=[user_id])


class MarketPrice(Base):
    """市场价格历史表"""

    __tablename__ = "market_prices"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    price = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class AIDecisionLog(Base):
    """AI 决策日志表"""

    __tablename__ = "ai_decision_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)  # 可为空，表示系统级决策
    prompt_name = Column(String(100), nullable=False)  # 使用的策略名称
    market_context = Column(Text, nullable=True)  # 市场上下文（价格、指标等）
    ai_reasoning = Column(Text, nullable=True)  # AI 推理过程
    decision = Column(String(20), nullable=False)  # 决策：BUY/SELL/HOLD
    action_taken = Column(Boolean, default=False, nullable=False)  # 是否实际执行
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # 关系
    user = relationship("User", back_populates="ai_decisions")


class AIConversation(Base):
    """AI 对话历史表"""

    __tablename__ = "ai_conversations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), nullable=False)  # user/assistant/system
    content = Column(Text, nullable=False)  # 对话内容
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # 关系
    user = relationship("User", back_populates="ai_conversations")
