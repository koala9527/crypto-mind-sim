"""交易展示与快照计算工具。"""

from __future__ import annotations

from datetime import datetime

from backend.core.models import (
    DEFAULT_LIQUIDATION_THRESHOLD,
    DEFAULT_TRADING_FEE_RATE,
    TradeSide,
)


def calculate_notional_value(price: float, quantity: float) -> float:
    return round(price * quantity, 8)


def calculate_fee(price: float, quantity: float, fee_rate: float = DEFAULT_TRADING_FEE_RATE) -> float:
    return round(calculate_notional_value(price, quantity) * fee_rate, 8)


def calculate_roi_pct(pnl: float, margin: float) -> float | None:
    if not margin:
        return None
    return round((pnl / margin) * 100, 4)


def calculate_liquidation_price(
    entry_price: float,
    leverage: int,
    side: TradeSide,
    liquidation_threshold: float = DEFAULT_LIQUIDATION_THRESHOLD,
) -> float | None:
    if not entry_price or leverage <= 0:
        return None

    move_ratio = liquidation_threshold / (leverage ** 2)
    if side == TradeSide.LONG:
        return round(entry_price * (1 - move_ratio), 8)
    if side == TradeSide.SHORT:
        return round(entry_price * (1 + move_ratio), 8)
    return None


def calculate_holding_seconds(start_time: datetime | None, end_time: datetime | None) -> int | None:
    if not start_time or not end_time:
        return None
    return max(int((end_time - start_time).total_seconds()), 0)


def get_risk_level(leverage: int) -> str:
    if leverage <= 3:
        return "LOW"
    if leverage <= 10:
        return "MEDIUM"
    return "HIGH"
