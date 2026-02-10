"""
市场数据 API 路由
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List, Dict
from backend.core.database import get_db
from backend.engine.engine import trading_engine
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/market", tags=["Market"])


class MarketDataResponse(BaseModel):
    """市场数据响应"""
    symbol: str
    timeframe: str
    timestamp: int
    current_price: float
    open: float
    high: float
    low: float
    volume: float
    indicators: Dict


@router.get("/data", response_model=MarketDataResponse)
async def get_market_data(
    symbol: str = Query("BTC/USDT", description="交易对"),
    timeframe: str = Query("1h", description="时间周期"),
    limit: int = Query(100, ge=10, le=500, description="K线数量")
):
    """
    获取市场数据，包括价格、成交量和技术指标

    技术指标包括：
    - ma5: 5日移动平均线
    - ma10: 10日移动平均线
    - ma30: 30日移动平均线
    - vol_ma10: 10日成交量均线
    - vol_ratio: 当前成交量与均线的比率
    - price_change_pct: 价格变化率
    - rsi: 相对强弱指标
    """
    data = trading_engine.fetch_market_data(symbol=symbol, timeframe=timeframe, limit=limit)

    if not data:
        # 返回模拟数据
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "timestamp": 0,
            "current_price": 0,
            "open": 0,
            "high": 0,
            "low": 0,
            "volume": 0,
            "indicators": {
                "ma5": None,
                "ma10": None,
                "ma30": None,
                "vol_ma10": None,
                "vol_ratio": None,
                "price_change_pct": None,
                "rsi": None
            }
        }

    return MarketDataResponse(**data)


@router.get("/ohlcv")
async def get_ohlcv(
    symbol: str = Query("BTC/USDT", description="交易对"),
    timeframe: str = Query("1h", description="时间周期"),
    limit: int = Query(100, ge=10, le=500, description="K线数量")
):
    """
    获取完整的OHLCV数据

    返回：
    - timestamps: 时间戳列表
    - opens: 开盘价列表
    - highs: 最高价列表
    - lows: 最低价列表
    - closes: 收盘价列表
    - volumes: 成交量列表
    """
    data = trading_engine.fetch_market_data(symbol=symbol, timeframe=timeframe, limit=limit)

    if not data:
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "ohlcv": {
                "timestamps": [],
                "opens": [],
                "highs": [],
                "lows": [],
                "closes": [],
                "volumes": []
            }
        }

    return {
        "symbol": data['symbol'],
        "timeframe": data['timeframe'],
        "ohlcv": data['ohlcv']
    }


@router.get("/price/{symbol}")
async def get_price(symbol: str):
    """
    获取指定交易对的当前价格

    Args:
        symbol: 交易对 (如 BTC/USDT)
    """
    price = trading_engine.fetch_current_price(symbol)

    if price is None:
        return {
            "symbol": symbol,
            "price": 0,
            "error": "无法获取价格"
        }

    return {
        "symbol": symbol,
        "price": price
    }
