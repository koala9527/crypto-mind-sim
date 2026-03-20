"""AI 相关 API 路由。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from backend.core.database import get_db
from backend.core.models import User, Position, MarketPrice
from backend.core.security import get_current_user
from backend.services.ai_service import ai_service, AVAILABLE_MODELS
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai", tags=["AI"])


class ModelInfo(BaseModel):
    """模型信息"""
    id: str
    name: str
    provider: str
    description: str
    icon: str


class MarketAnalysisRequest(BaseModel):
    """市场分析请求"""
    user_id: int
    api_key: str
    base_url: str = ""
    model: Optional[str] = None


class MarketAnalysisResponse(BaseModel):
    """市场分析响应"""
    trend: str
    volatility: str
    suggestion: str
    reasoning: str
    model_used: str


class TradingAdviceRequest(BaseModel):
    """交易建议请求"""
    user_id: int
    api_key: str
    base_url: str = ""
    risk_tolerance: str = "medium"
    model: Optional[str] = None


class TradingAdviceResponse(BaseModel):
    """交易建议响应"""
    action: str
    direction: Optional[str] = None
    position_size: Optional[float] = None
    leverage: Optional[int] = None
    stop_loss: Optional[float] = None
    reasoning: str
    model_used: str


@router.get("/models", response_model=List[ModelInfo])
async def get_available_models():
    """获取可用的 AI 模型列表"""
    return await ai_service.list_models()


@router.post("/analyze", response_model=MarketAnalysisResponse)
async def analyze_market(
    request: MarketAnalysisRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    AI 市场分析

    基于当前市场数据和用户持仓，进行智能分析并给出市场判断
    """
    # 获取用户信息
    if current_user.id != request.user_id:
        raise HTTPException(status_code=403, detail="无权分析其他用户数据")

    user = current_user

    # 获取当前价格
    latest_price = (
        db.query(MarketPrice)
        .order_by(MarketPrice.timestamp.desc())
        .first()
    )

    if not latest_price:
        raise HTTPException(status_code=500, detail="无法获取市场价格")

    # 获取历史价格
    price_history = (
        db.query(MarketPrice)
        .order_by(MarketPrice.timestamp.desc())
        .limit(50)
        .all()
    )

    # 获取用户持仓
    positions = (
        db.query(Position)
        .filter(Position.user_id == current_user.id, Position.is_open == True)
        .all()
    )

    # 格式化数据
    price_data = [
        {"price": p.price, "timestamp": str(p.timestamp)}
        for p in reversed(price_history)
    ]

    position_data = [
        {
            "side": p.side.value,
            "quantity": p.quantity,
            "entry_price": p.entry_price,
            "unrealized_pnl": p.unrealized_pnl
        }
        for p in positions
    ]

    # 调用 AI 分析
    try:
        analysis = await ai_service.analyze_market(
            current_price=latest_price.price,
            price_history=price_data,
            user_positions=position_data,
            api_key=request.api_key,
            base_url=request.base_url,
            model=request.model
        )

        return MarketAnalysisResponse(
            **analysis,
            model_used=request.model or ai_service.default_model
        )

    except Exception as e:
        logger.error(f"AI 分析失败: {e}")
        raise HTTPException(status_code=500, detail=f"AI 分析失败: {str(e)}")


@router.post("/advice", response_model=TradingAdviceResponse)
async def get_trading_advice(
    request: TradingAdviceRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    AI 交易建议

    基于市场分析和用户资金情况，给出具体的交易建议
    """
    # 获取用户信息
    if current_user.id != request.user_id:
        raise HTTPException(status_code=403, detail="无权分析其他用户数据")

    user = current_user

    # 先进行市场分析
    latest_price = (
        db.query(MarketPrice)
        .order_by(MarketPrice.timestamp.desc())
        .first()
    )

    if not latest_price:
        raise HTTPException(status_code=500, detail="无法获取市场价格")

    # 获取历史价格用于分析
    price_history = (
        db.query(MarketPrice)
        .order_by(MarketPrice.timestamp.desc())
        .limit(50)
        .all()
    )

    positions = (
        db.query(Position)
        .filter(Position.user_id == current_user.id, Position.is_open == True)
        .all()
    )

    price_data = [
        {"price": p.price, "timestamp": str(p.timestamp)}
        for p in reversed(price_history)
    ]

    position_data = [
        {
            "side": p.side.value,
            "quantity": p.quantity,
            "entry_price": p.entry_price,
            "unrealized_pnl": p.unrealized_pnl
        }
        for p in positions
    ]

    # 先分析市场
    try:
        market_analysis = await ai_service.analyze_market(
            current_price=latest_price.price,
            price_history=price_data,
            user_positions=position_data,
            api_key=request.api_key,
            base_url=request.base_url,
            model=request.model
        )

        # 基于市场分析获取交易建议
        market_data = {
            "current_price": latest_price.price,
            "trend": market_analysis.get("trend", "unknown"),
            "volatility": market_analysis.get("volatility", "unknown")
        }

        advice = await ai_service.get_trading_advice(
            market_data=market_data,
            user_balance=user.balance,
            api_key=request.api_key,
            base_url=request.base_url,
            risk_tolerance=request.risk_tolerance,
            model=request.model
        )

        return TradingAdviceResponse(
            **advice,
            model_used=request.model or ai_service.default_model
        )

    except Exception as e:
        logger.error(f"获取交易建议失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取交易建议失败: {str(e)}")
