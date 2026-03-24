"""
策略管理 API 路由
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from backend.core.database import get_db
from backend.core.models import User, PromptConfig, PromptRevisionHistory, get_local_time
from backend.core.security import require_same_user
from backend.core.trading_pairs import DEFAULT_SYMBOL, POPULAR_TRADING_PAIRS, POPULAR_SYMBOL_CODES
from backend.services.ai_service import AVAILABLE_MODELS
from backend.services.prompt_revision_service import record_prompt_revision
from backend.utils.init_prompts import DEFAULT_PROMPTS
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/strategies", tags=["Strategies"])


class StrategyCreate(BaseModel):
    """创建策略"""
    name: str = Field(..., min_length=1, max_length=100, description="策略名称")
    description: Optional[str] = Field(None, description="策略描述")
    prompt_text: str = Field(..., min_length=1, description="AI 提示词")
    base_prompt_text: Optional[str] = Field(None, description="提示词风格基准")
    symbol: str = Field(default=DEFAULT_SYMBOL, description="交易对")
    execution_interval: int = Field(default=1, ge=1, description="执行频率（分钟，最小1分钟）")
    auto_optimize_prompt: bool = Field(default=False, description="是否自动修正提示词")
    prompt_optimization_interval: int = Field(default=1, ge=1, description="每多少次决策修正一次")
    prompt_optimization_include_hold: bool = Field(default=True, description="HOLD 是否计入修正次数")


class StrategyUpdate(BaseModel):
    """更新策略"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    prompt_text: Optional[str] = Field(None, min_length=1)
    base_prompt_text: Optional[str] = Field(None, min_length=1)
    symbol: Optional[str] = None
    execution_interval: Optional[int] = Field(None, ge=1, description="执行频率（分钟，最小1分钟）")
    auto_optimize_prompt: Optional[bool] = None
    prompt_optimization_interval: Optional[int] = Field(None, ge=1)
    prompt_optimization_include_hold: Optional[bool] = None
    revision_source: Optional[str] = None
    is_active: Optional[bool] = None


class StrategyResponse(BaseModel):
    """策略响应"""
    id: int
    user_id: int
    name: str
    description: Optional[str]
    prompt_text: str
    base_prompt_text: Optional[str]
    symbol: str
    ai_model: str
    execution_interval: int
    auto_optimize_prompt: bool
    prompt_optimization_interval: int
    prompt_optimization_include_hold: bool
    last_prompt_optimized_at: Optional[datetime]
    prompt_revision_count: int
    is_active: bool
    last_executed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PromptRevisionHistoryResponse(BaseModel):
    id: int
    strategy_id: int
    user_id: int
    revision_no: int
    source: str
    summary: Optional[str]
    previous_prompt_text: Optional[str]
    prompt_text: str
    base_prompt_text: Optional[str]
    created_at: datetime

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


# 支持的交易对列表（主流高流动性 USDT 交易对）
AVAILABLE_SYMBOLS = POPULAR_TRADING_PAIRS


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
    db: Session = Depends(get_db),
    current_user: User = Depends(require_same_user)
):
    """获取用户的所有策略"""
    strategies = db.query(PromptConfig).filter(
        PromptConfig.user_id == current_user.id
    ).order_by(PromptConfig.created_at.desc()).all()

    return strategies


@router.get("/{strategy_id}", response_model=StrategyResponse)
async def get_strategy(
    strategy_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_same_user)
):
    """获取单个策略详情"""
    strategy = db.query(PromptConfig).filter(
        PromptConfig.id == strategy_id,
        PromptConfig.user_id == current_user.id
    ).first()

    if not strategy:
        raise HTTPException(status_code=404, detail="策略不存在")

    return strategy


@router.get("/{strategy_id}/prompt-revisions", response_model=List[PromptRevisionHistoryResponse])
async def get_strategy_prompt_revisions(
    strategy_id: int,
    user_id: int,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_same_user)
):
    """获取策略整个生命周期内的提示词修正历史。"""
    strategy = db.query(PromptConfig).filter(
        PromptConfig.id == strategy_id,
        PromptConfig.user_id == current_user.id,
    ).first()

    if not strategy:
        raise HTTPException(status_code=404, detail="策略不存在")

    query_limit = min(max(limit, 1), 300)
    return (
        db.query(PromptRevisionHistory)
        .filter(
            PromptRevisionHistory.strategy_id == strategy.id,
            PromptRevisionHistory.user_id == current_user.id,
        )
        .order_by(PromptRevisionHistory.created_at.desc(), PromptRevisionHistory.id.desc())
        .limit(query_limit)
        .all()
    )


@router.post("", response_model=StrategyResponse, status_code=status.HTTP_201_CREATED)
async def create_strategy(
    user_id: int,
    strategy: StrategyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_same_user)
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
    user = current_user

    # 检查用户是否已有策略
    existing = db.query(PromptConfig).filter(
        PromptConfig.user_id == current_user.id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="您已经有一个策略，请编辑现有策略或删除后再创建")

    prompt_text = strategy.prompt_text.strip()
    base_prompt_text = (strategy.base_prompt_text or prompt_text).strip()

    # 创建策略
    new_strategy = PromptConfig(
        user_id=current_user.id,
        name=strategy.name,
        description=strategy.description,
        prompt_text=prompt_text,
        base_prompt_text=base_prompt_text,
        symbol=strategy.symbol,
        ai_model="claude-4.5-opus",  # 占位，实际执行时用用户配置的模型
        execution_interval=strategy.execution_interval,
        auto_optimize_prompt=strategy.auto_optimize_prompt,
        prompt_optimization_interval=strategy.prompt_optimization_interval,
        prompt_optimization_include_hold=strategy.prompt_optimization_include_hold,
        is_active=True
    )

    db.add(new_strategy)
    db.flush()
    record_prompt_revision(
        db,
        strategy=new_strategy,
        source="CREATE",
        summary="策略创建，记录初始提示词版本",
        prompt_text=new_strategy.prompt_text,
        previous_prompt_text=None,
        base_prompt_text=new_strategy.base_prompt_text,
    )
    db.commit()
    db.refresh(new_strategy)

    logger.info(f"用户 {user.username} 创建策略: {new_strategy.name}")
    return new_strategy


@router.put("/{strategy_id}", response_model=StrategyResponse)
async def update_strategy(
    strategy_id: int,
    user_id: int,
    strategy_update: StrategyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_same_user)
):
    """更新策略"""
    strategy = db.query(PromptConfig).filter(
        PromptConfig.id == strategy_id,
        PromptConfig.user_id == current_user.id
    ).first()

    if not strategy:
        raise HTTPException(status_code=404, detail="策略不存在")

    # 更新字段
    update_data = strategy_update.model_dump(exclude_unset=True)
    revision_source = update_data.pop("revision_source", None) or "MANUAL_UPDATE"
    previous_prompt_text = strategy.prompt_text
    previous_base_prompt_text = strategy.base_prompt_text

    # 验证交易对
    if "symbol" in update_data:
        if update_data["symbol"] not in POPULAR_SYMBOL_CODES:
            raise HTTPException(status_code=400, detail=f"不支持的交易对: {update_data['symbol']}")

    # 检查名称重复
    if "name" in update_data:
        existing = db.query(PromptConfig).filter(
            PromptConfig.user_id == current_user.id,
            PromptConfig.name == update_data["name"],
            PromptConfig.id != strategy_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="策略名称已存在")

    if "base_prompt_text" in update_data:
        update_data["base_prompt_text"] = update_data["base_prompt_text"].strip()

    if "prompt_text" in update_data and update_data["prompt_text"]:
        update_data["prompt_text"] = update_data["prompt_text"].strip()

    if "base_prompt_text" not in update_data and "prompt_text" in update_data:
        update_data["base_prompt_text"] = strategy.base_prompt_text or strategy.prompt_text

    if "prompt_text" in update_data or "base_prompt_text" in update_data:
        strategy.prompt_revision_count = 0
        strategy.last_prompt_optimized_at = None

    for key, value in update_data.items():
        setattr(strategy, key, value)

    if strategy.prompt_text != previous_prompt_text or strategy.base_prompt_text != previous_base_prompt_text:
        summary_map = {
            "MANUAL_UPDATE": "用户手动修改提示词",
            "RESET_DEFAULT": "恢复为预设模板提示词",
            "CREATE": "策略创建初始版本",
            "AUTO_OPTIMIZE": "系统根据历史表现自动修正提示词",
        }
        record_prompt_revision(
            db,
            strategy=strategy,
            source=revision_source,
            summary=summary_map.get(revision_source, "提示词版本已更新"),
            prompt_text=strategy.prompt_text,
            previous_prompt_text=previous_prompt_text,
            base_prompt_text=strategy.base_prompt_text,
        )

    strategy.updated_at = get_local_time()
    db.commit()
    db.refresh(strategy)

    logger.info(f"更新策略: {strategy.name}")
    return strategy


@router.delete("/{strategy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_strategy(
    strategy_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_same_user)
):
    """删除策略"""
    strategy = db.query(PromptConfig).filter(
        PromptConfig.id == strategy_id,
        PromptConfig.user_id == current_user.id
    ).first()

    if not strategy:
        raise HTTPException(status_code=404, detail="策略不存在")

    db.query(PromptRevisionHistory).filter(PromptRevisionHistory.strategy_id == strategy.id).delete(synchronize_session=False)
    db.delete(strategy)
    db.commit()

    logger.info(f"删除策略: {strategy.name}")
    return None


@router.post("/{strategy_id}/activate", response_model=StrategyResponse)
async def activate_strategy(
    strategy_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_same_user)
):
    """
    激活策略

    每个用户只有一个策略，直接激活
    """
    strategy = db.query(PromptConfig).filter(
        PromptConfig.id == strategy_id,
        PromptConfig.user_id == current_user.id
    ).first()

    if not strategy:
        raise HTTPException(status_code=404, detail="策略不存在")

    # 激活策略
    strategy.is_active = True
    strategy.updated_at = get_local_time()

    db.commit()
    db.refresh(strategy)

    logger.info(f"激活策略: {strategy.name}")
    return strategy


@router.post("/{strategy_id}/deactivate", response_model=StrategyResponse)
async def deactivate_strategy(
    strategy_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_same_user)
):
    """停用策略"""
    strategy = db.query(PromptConfig).filter(
        PromptConfig.id == strategy_id,
        PromptConfig.user_id == current_user.id
    ).first()

    if not strategy:
        raise HTTPException(status_code=404, detail="策略不存在")

    strategy.is_active = False
    strategy.updated_at = get_local_time()

    db.commit()
    db.refresh(strategy)

    logger.info(f"停用策略: {strategy.name}")
    return strategy
