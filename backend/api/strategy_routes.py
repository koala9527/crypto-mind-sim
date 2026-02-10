"""
策略管理 API 路由
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from backend.core.database import get_db
from backend.core.models import User, PromptConfig
from backend.services.ai_service import AVAILABLE_MODELS
from backend.utils.init_prompts import DEFAULT_PROMPTS
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/strategies", tags=["Strategies"])


class StrategyCreate(BaseModel):
    """创建策略"""
    name: str = Field(..., min_length=1, max_length=100, description="策略名称")
    description: Optional[str] = Field(None, description="策略描述")
    prompt_text: str = Field(..., min_length=1, description="AI 提示词")
    symbol: str = Field(default="BTC/USDT", description="交易对")
    ai_model: str = Field(default="claude-4.5-opus", description="AI 模型")
    execution_interval: int = Field(default=60, ge=60, description="执行频率（秒，最小60秒）")


class StrategyUpdate(BaseModel):
    """更新策略"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    prompt_text: Optional[str] = Field(None, min_length=1)
    symbol: Optional[str] = None
    ai_model: Optional[str] = None
    execution_interval: Optional[int] = Field(None, ge=60)
    is_active: Optional[bool] = None


class StrategyResponse(BaseModel):
    """策略响应"""
    id: int
    user_id: int
    name: str
    description: Optional[str]
    prompt_text: str
    symbol: str
    ai_model: str
    execution_interval: int
    is_active: bool
    last_executed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SymbolInfo(BaseModel):
    """交易对信息"""
    symbol: str
    name: str
    description: str


class PresetStrategyInfo(BaseModel):
    """预设策略信息（仅包含策略描述和提示词）"""
    name: str
    description: str
    prompt_text: str


# 支持的交易对列表 (Top 10 加密货币)
AVAILABLE_SYMBOLS = [
    {"symbol": "BTC/USDT", "name": "比特币", "description": "Bitcoin"},
    {"symbol": "ETH/USDT", "name": "以太坊", "description": "Ethereum"},
    {"symbol": "BNB/USDT", "name": "币安币", "description": "Binance Coin"},
    {"symbol": "SOL/USDT", "name": "Solana", "description": "Solana"},
    {"symbol": "XRP/USDT", "name": "瑞波币", "description": "Ripple"},
    {"symbol": "ADA/USDT", "name": "艾达币", "description": "Cardano"},
    {"symbol": "AVAX/USDT", "name": "雪崩币", "description": "Avalanche"},
    {"symbol": "DOT/USDT", "name": "波卡", "description": "Polkadot"},
    {"symbol": "POL/USDT", "name": "马蹄币", "description": "Polygon"},  # MATIC已更名为POL
    {"symbol": "LINK/USDT", "name": "链环", "description": "Chainlink"},
]


@router.get("/symbols", response_model=List[SymbolInfo])
async def get_available_symbols():
    """获取支持的交易对列表"""
    return AVAILABLE_SYMBOLS


@router.get("/presets", response_model=List[PresetStrategyInfo])
async def get_preset_strategies():
    """获取预设策略模板列表"""
    return DEFAULT_PROMPTS


@router.get("", response_model=List[StrategyResponse])
async def get_user_strategies(
    user_id: int,
    db: Session = Depends(get_db)
):
    """获取用户的所有策略"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    strategies = db.query(PromptConfig).filter(
        PromptConfig.user_id == user_id
    ).order_by(PromptConfig.created_at.desc()).all()

    return strategies


@router.get("/{strategy_id}", response_model=StrategyResponse)
async def get_strategy(
    strategy_id: int,
    user_id: int,
    db: Session = Depends(get_db)
):
    """获取单个策略详情"""
    strategy = db.query(PromptConfig).filter(
        PromptConfig.id == strategy_id,
        PromptConfig.user_id == user_id
    ).first()

    if not strategy:
        raise HTTPException(status_code=404, detail="策略不存在")

    return strategy


@router.post("", response_model=StrategyResponse, status_code=status.HTTP_201_CREATED)
async def create_strategy(
    user_id: int,
    strategy: StrategyCreate,
    db: Session = Depends(get_db)
):
    """
    创建新策略

    每个用户只能创建一个策略，策略可以配置：
    - 策略名称和描述
    - AI 提示词
    - 交易对
    - AI 模型
    - 执行频率（最小1分钟）
    """
    # 验证用户存在
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 检查用户是否已有策略
    existing = db.query(PromptConfig).filter(
        PromptConfig.user_id == user_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="您已经有一个策略，请编辑现有策略或删除后再创建")

    # 验证模型是否支持
    if strategy.ai_model not in AVAILABLE_MODELS:
        raise HTTPException(status_code=400, detail=f"不支持的模型: {strategy.ai_model}")

    # 验证交易对是否支持
    supported_symbols = [s["symbol"] for s in AVAILABLE_SYMBOLS]
    if strategy.symbol not in supported_symbols:
        raise HTTPException(status_code=400, detail=f"不支持的交易对: {strategy.symbol}")

    # 创建策略
    new_strategy = PromptConfig(
        user_id=user_id,
        name=strategy.name,
        description=strategy.description,
        prompt_text=strategy.prompt_text,
        symbol=strategy.symbol,
        ai_model=strategy.ai_model,
        execution_interval=strategy.execution_interval,
        is_active=True  # 默认激活（因为只有一个策略）
    )

    db.add(new_strategy)
    db.commit()
    db.refresh(new_strategy)

    logger.info(f"用户 {user.username} 创建策略: {new_strategy.name}")
    return new_strategy


@router.put("/{strategy_id}", response_model=StrategyResponse)
async def update_strategy(
    strategy_id: int,
    user_id: int,
    strategy_update: StrategyUpdate,
    db: Session = Depends(get_db)
):
    """更新策略"""
    strategy = db.query(PromptConfig).filter(
        PromptConfig.id == strategy_id,
        PromptConfig.user_id == user_id
    ).first()

    if not strategy:
        raise HTTPException(status_code=404, detail="策略不存在")

    # 更新字段
    update_data = strategy_update.dict(exclude_unset=True)

    # 验证模型
    if "ai_model" in update_data and update_data["ai_model"] not in AVAILABLE_MODELS:
        raise HTTPException(status_code=400, detail=f"不支持的模型: {update_data['ai_model']}")

    # 验证交易对
    if "symbol" in update_data:
        supported_symbols = [s["symbol"] for s in AVAILABLE_SYMBOLS]
        if update_data["symbol"] not in supported_symbols:
            raise HTTPException(status_code=400, detail=f"不支持的交易对: {update_data['symbol']}")

    # 检查名称重复
    if "name" in update_data:
        existing = db.query(PromptConfig).filter(
            PromptConfig.user_id == user_id,
            PromptConfig.name == update_data["name"],
            PromptConfig.id != strategy_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="策略名称已存在")

    for key, value in update_data.items():
        setattr(strategy, key, value)

    strategy.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(strategy)

    logger.info(f"更新策略: {strategy.name}")
    return strategy


@router.delete("/{strategy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_strategy(
    strategy_id: int,
    user_id: int,
    db: Session = Depends(get_db)
):
    """删除策略"""
    strategy = db.query(PromptConfig).filter(
        PromptConfig.id == strategy_id,
        PromptConfig.user_id == user_id
    ).first()

    if not strategy:
        raise HTTPException(status_code=404, detail="策略不存在")

    db.delete(strategy)
    db.commit()

    logger.info(f"删除策略: {strategy.name}")
    return None


@router.post("/{strategy_id}/activate", response_model=StrategyResponse)
async def activate_strategy(
    strategy_id: int,
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    激活策略

    每个用户只有一个策略，直接激活
    """
    strategy = db.query(PromptConfig).filter(
        PromptConfig.id == strategy_id,
        PromptConfig.user_id == user_id
    ).first()

    if not strategy:
        raise HTTPException(status_code=404, detail="策略不存在")

    # 激活策略
    strategy.is_active = True
    strategy.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(strategy)

    logger.info(f"激活策略: {strategy.name}")
    return strategy


@router.post("/{strategy_id}/deactivate", response_model=StrategyResponse)
async def deactivate_strategy(
    strategy_id: int,
    user_id: int,
    db: Session = Depends(get_db)
):
    """停用策略"""
    strategy = db.query(PromptConfig).filter(
        PromptConfig.id == strategy_id,
        PromptConfig.user_id == user_id
    ).first()

    if not strategy:
        raise HTTPException(status_code=404, detail="策略不存在")

    strategy.is_active = False
    strategy.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(strategy)

    logger.info(f"停用策略: {strategy.name}")
    return strategy
