"""策略执行器"""

from __future__ import annotations

import json
import logging
import re
from collections import Counter
from datetime import timedelta

from sqlalchemy import or_
from sqlalchemy.orm import Session

from backend.core.database import SessionLocal
from backend.core.models import (
    AIDecisionLog,
    MarketPrice,
    Position,
    PromptConfig,
    Trade,
    TradeSide,
    TradeType,
    User,
    get_local_time,
)
from backend.core.trade_utils import (
    calculate_fee,
    calculate_holding_seconds,
    calculate_liquidation_price,
    calculate_notional_value,
    calculate_roi_pct,
)
from backend.engine.engine import trading_engine
from backend.services.ai_service import AIAPIError, ai_service
from backend.services.prompt_revision_service import record_prompt_revision

logger = logging.getLogger(__name__)

MAX_HISTORY_TRADE_RECORDS = 120
MAX_HISTORY_DECISION_RECORDS = 60
MAX_HISTORY_EVENT_LINES = 6


def _safe_average(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _safe_load_market_data(payload: str | None) -> dict:
    if not payload:
        return {}
    try:
        return json.loads(payload)
    except Exception:
        return {}


def _short_text(text: str | None, limit: int = 88) -> str:
    if not text:
        return ""
    normalized = re.sub(r"\s+", " ", text).strip()
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[: limit - 1]}…"


def _format_duration(seconds: int | None) -> str:
    if not seconds:
        return "-"
    if seconds < 3600:
        return f"{seconds // 60}m"
    return f"{seconds / 3600:.1f}h"


def _extract_trade_note(trade: Trade) -> str:
    data = _safe_load_market_data(trade.market_data)
    if trade.trade_type == TradeType.ERROR:
        return _short_text(data.get("error") or data.get("exception") or "执行异常")
    if trade.trade_type == TradeType.HOLD:
        return _short_text(data.get("reasoning") or data.get("decision") or "继续观望")
    if trade.trade_type == TradeType.CLOSE:
        return _short_text(data.get("close_reason") or trade.close_reason or "正常平仓")
    if trade.trade_type == TradeType.OPEN:
        side = trade.position_side.value if trade.position_side else trade.side.value
        return f"{side} {trade.leverage}x"
    return ""


def count_prompt_optimization_decisions(db: Session, strategy: PromptConfig) -> int:
    decisions = db.query(AIDecisionLog).filter(
        AIDecisionLog.user_id == strategy.user_id,
        AIDecisionLog.prompt_name == strategy.name,
    )
    if strategy.last_prompt_optimized_at:
        decisions = decisions.filter(AIDecisionLog.created_at > strategy.last_prompt_optimized_at)
    rows = decisions.order_by(AIDecisionLog.created_at.desc()).limit(MAX_HISTORY_DECISION_RECORDS).all()
    if strategy.prompt_optimization_include_hold:
        return len(rows)
    return sum(1 for row in rows if (row.decision or "").upper() != "HOLD")


def should_optimize_prompt(db: Session, strategy: PromptConfig) -> bool:
    if not strategy.auto_optimize_prompt:
        return False
    if not strategy.last_prompt_optimized_at:
        return True
    interval = max(strategy.prompt_optimization_interval or 1, 1)
    return count_prompt_optimization_decisions(db, strategy) >= interval


def build_strategy_history_snapshot(db: Session, strategy: PromptConfig) -> dict:
    trades = (
        db.query(Trade)
        .filter(
            Trade.user_id == strategy.user_id,
            Trade.symbol == strategy.symbol,
            Trade.trade_type.in_([TradeType.OPEN, TradeType.CLOSE, TradeType.HOLD, TradeType.ERROR]),
            or_(
                Trade.execution_source == "AI",
                Trade.trade_type.in_([TradeType.HOLD, TradeType.ERROR]),
            ),
        )
        .order_by(Trade.created_at.desc())
        .limit(MAX_HISTORY_TRADE_RECORDS)
        .all()
    )
    decisions = (
        db.query(AIDecisionLog)
        .filter(
            AIDecisionLog.user_id == strategy.user_id,
            AIDecisionLog.prompt_name == strategy.name,
        )
        .order_by(AIDecisionLog.created_at.desc())
        .limit(MAX_HISTORY_DECISION_RECORDS)
        .all()
    )

    closes = [trade for trade in trades if trade.trade_type == TradeType.CLOSE]
    pnl_values = [trade.pnl or 0.0 for trade in closes]
    roi_values = [trade.roi_pct for trade in closes if trade.roi_pct is not None]
    holding_values = [trade.holding_seconds for trade in closes if trade.holding_seconds]
    realized_fee = sum((trade.fee_paid or 0.0) for trade in trades)
    total_realized_pnl = sum(pnl_values)
    fee_pressure = realized_fee / max(abs(total_realized_pnl), 1.0)
    win_count = sum(1 for trade in closes if (trade.pnl or 0.0) > 0)

    recent_actions = [(row.decision or "").upper() for row in decisions[:20] if row.decision]
    recent_action_counter = Counter(recent_actions)

    event_lines = []
    for trade in reversed(trades[:MAX_HISTORY_EVENT_LINES]):
        timestamp = trade.created_at.strftime("%m-%d %H:%M") if trade.created_at else "-"
        note = _extract_trade_note(trade)
        if trade.trade_type == TradeType.OPEN:
            event_lines.append(
                f"- {timestamp} OPEN qty {trade.quantity or 0:.6f} / lev {trade.leverage}x / fee ${trade.fee_paid or 0:,.2f} / {note}"
            )
        elif trade.trade_type == TradeType.CLOSE:
            event_lines.append(
                f"- {timestamp} CLOSE pnl ${trade.pnl or 0:,.2f} / roi {trade.roi_pct or 0:.2f}% / {note}"
            )
        elif trade.trade_type == TradeType.HOLD:
            event_lines.append(f"- {timestamp} HOLD / {note}")
        else:
            event_lines.append(f"- {timestamp} ERROR / {note}")

    insights: list[str] = []
    if closes and len(closes) >= 3 and (win_count / max(len(closes), 1)) < 0.4:
        insights.append("最近平仓胜率偏低，需要收紧开仓条件并减少低质量试单")
    if realized_fee > 0 and fee_pressure >= 0.35:
        insights.append("最近平仓胜率偏低，需要收紧开仓条件并减少低质量试单")
    if recent_action_counter.get("HOLD", 0) >= 8:
        insights.append("最近 HOLD 次数较多，说明当前行情不清晰，应继续提高入场门槛")
    if recent_action_counter.get("ERROR", 0) > 0:
        insights.append("最近存在执行异常，需要检查输出格式、接口稳定性与 JSON 合法性")

    return {
        "trade_count": len(trades),
        "decision_count": len(decisions),
        "open_count": sum(1 for trade in trades if trade.trade_type == TradeType.OPEN),
        "close_count": len(closes),
        "hold_count": sum(1 for trade in trades if trade.trade_type == TradeType.HOLD),
        "error_count": sum(1 for trade in trades if trade.trade_type == TradeType.ERROR),
        "win_rate": (win_count / len(closes) * 100) if closes else 0.0,
        "total_pnl": total_realized_pnl,
        "avg_roi": _safe_average(roi_values),
        "avg_holding_seconds": int(_safe_average(holding_values)) if holding_values else 0,
        "total_fee": realized_fee,
        "fee_pressure": fee_pressure,
        "recent_action_counter": dict(recent_action_counter),
        "recent_actions": recent_actions,
        "insights": insights,
        "event_lines": event_lines,
    }


def format_strategy_history_context(snapshot: dict) -> str:
    if not snapshot:
        return "暂无可用的策略历史摘要"

    action_counter = snapshot.get("recent_action_counter", {})
    action_text = " / ".join(
        [
            f"OPEN {action_counter.get('OPEN', 0)}",
            f"CLOSE {action_counter.get('CLOSE', 0)}",
            f"HOLD {action_counter.get('HOLD', 0)}",
            f"ERROR {action_counter.get('ERROR', 0)}",
        ]
    )
    insights = snapshot.get("insights") or ["暂无显著风险提示"]
    event_lines = snapshot.get("event_lines") or ["- 暂无关键事件"]

    return "\n".join(
        [
            "## 策略执行历史摘要",
            f"- 样本统计: {snapshot.get('trade_count', 0)} 条 AI 交易记录 / {snapshot.get('decision_count', 0)} 条 AI 决策记录",
            f"- 动作分布: {action_text}",
            f"- 绩效表现: 胜率 {snapshot.get('win_rate', 0):.2f}% / 总盈亏 ${snapshot.get('total_pnl', 0):,.2f} / 平均 ROI {snapshot.get('avg_roi', 0):.2f}% / 平均持仓 {_format_duration(snapshot.get('avg_holding_seconds', 0))}",
            f"- 成本压力: 累计手续费 ${snapshot.get('total_fee', 0):,.2f} / 手续费压力 {snapshot.get('fee_pressure', 0):.2f}",
            f"- 最近 20 次动作: {action_text}",
            "- 风险提示: " + "；".join(insights),
            "- 最近关键事件:",
            *event_lines,
        ]
    )


def strip_json_comments(json_str: str) -> str:
    json_str = re.sub(r"//.*?$", "", json_str, flags=re.M)
    json_str = re.sub(r"/\*.*?\*/", "", json_str, flags=re.S)
    return json_str.strip()


def extract_json_from_content(content: str) -> str:
    if not content:
        return "{}"
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, flags=re.S)
    if fenced:
        return strip_json_comments(fenced.group(1))
    start = content.find("{")
    end = content.rfind("}")
    if start != -1 and end != -1 and end > start:
        return strip_json_comments(content[start : end + 1])
    return strip_json_comments(content)


def extract_prompt_text(content: str) -> str:
    if not content:
        return ""
    text = content.strip()
    fenced = re.search(r"```(?:text|markdown)?\s*(.*?)\s*```", text, flags=re.S)
    if fenced:
        text = fenced.group(1).strip()
    return text.strip()


async def maybe_optimize_strategy_prompt(
    db: Session,
    strategy: PromptConfig,
    user: User,
    history_snapshot: dict,
) -> str:
    base_prompt = strategy.base_prompt_text or strategy.prompt_text or ""
    current_prompt = strategy.prompt_text or base_prompt
    if not strategy.auto_optimize_prompt or not user.ai_api_key:
        return current_prompt
    if not should_optimize_prompt(db, strategy):
        return current_prompt

    history_context = format_strategy_history_context(history_snapshot)
    messages = [
        {
            "role": "system",
            "content": """你是一个交易策略提示词修正助手，只能围绕当前策略既有风格进行微调。
要求：
1. 必须保持策略名称对应的交易风格，不要改造成其他风格模板
2. 必须结合历史交易表现、手续费压力和决策质量做小步修正
3. 输出结果必须是可直接替换的完整提示词正文
4. 不要输出 JSON、解释、前言或额外标记""",
        },
        {
            "role": "user",
            "content": f"""策略名称: {strategy.name}
策略描述: {strategy.description or '-'}
交易对: {strategy.symbol}

风格基准提示词：
{base_prompt}

当前生效提示词：
{current_prompt}

历史表现摘要：
{history_context}

请基于以上信息修正提示词，但必须继续保持当前策略名称对应的风格。
要求：
- 保留原有交易风格与核心方法
- 重点修正胜率、手续费、频繁交易和风险控制问题
- 输出新的完整提示词正文
- 不要输出任何解释、标题或额外格式""",
        },
    ]

    try:
        result = await ai_service.chat_completion(
            messages=messages,
            api_key=user.ai_api_key,
            base_url=user.ai_base_url or "",
            model=user.ai_model or "claude-4.5-opus",
            temperature=0.2,
            max_tokens=1400,
        )
        revised_prompt = extract_prompt_text(result["choices"][0]["message"]["content"])
        strategy.last_prompt_optimized_at = get_local_time()
        if revised_prompt and revised_prompt != current_prompt:
            strategy.prompt_text = revised_prompt
            strategy.prompt_revision_count = (strategy.prompt_revision_count or 0) + 1
            summary = "系统根据历史表现自动修正提示词"
            if history_snapshot.get("insights"):
                summary = "；".join(history_snapshot["insights"][:3])
            record_prompt_revision(
                db=db,
                strategy=strategy,
                source="AUTO_OPTIMIZE",
                summary=summary,
                prompt_text=revised_prompt,
                previous_prompt_text=current_prompt,
                base_prompt_text=base_prompt,
            )
        db.commit()
        db.refresh(strategy)
        return strategy.prompt_text or current_prompt
    except Exception as exc:
        logger.warning("策略 %s 自动修正提示词失败: %s", strategy.name, exc)
        db.rollback()
        return current_prompt


async def execute_active_strategies():
    db = SessionLocal()
    try:
        active_ids = [
            strategy.id
            for strategy in db.query(PromptConfig).filter(PromptConfig.is_active.is_(True)).all()
            if should_execute_strategy(strategy)
        ]
    finally:
        db.close()

    for strategy_id in active_ids:
        db = SessionLocal()
        try:
            strategy = db.query(PromptConfig).filter(PromptConfig.id == strategy_id).first()
            if strategy:
                await execute_single_strategy(db, strategy)
        except Exception as exc:
            logger.exception("执行策略 %s 失败: %s", strategy_id, exc)
            db.rollback()
        finally:
            db.close()


def should_execute_strategy(strategy: PromptConfig) -> bool:
    if not strategy.is_active:
        return False
    if not strategy.last_executed_at:
        return True
    interval = max(strategy.execution_interval or 1, 1)
    return get_local_time() - strategy.last_executed_at >= timedelta(minutes=interval)


def format_price_history(history: list) -> str:
    if not history:
        return "暂无价格历史"
    return "\n".join(
        f"  {item.get('timestamp', '-')}: ${item.get('price', 0):,.2f}" for item in history
    )


def format_positions(positions: list) -> str:
    if not positions:
        return "暂无持仓"
    lines = []
    for pos in positions:
        lines.append(
            f"- {pos.get('symbol')} / {pos.get('side')} / qty {pos.get('quantity', 0):.6f} / entry ${pos.get('entry_price', 0):,.2f} / lev {pos.get('leverage', 1)}x / margin ${pos.get('margin', 0):,.2f} / pnl ${pos.get('unrealized_pnl', 0):,.2f}"
        )
    return "\n".join(lines)


async def execute_single_strategy(db: Session, strategy: PromptConfig):
    user = db.query(User).filter(User.id == strategy.user_id).first()
    if not user:
        return

    market_data = trading_engine.fetch_market_data(strategy.symbol)
    current_price = market_data["current_price"] if market_data else trading_engine.fetch_current_price(strategy.symbol)
    if current_price is None:
        logger.warning("策略 %s 获取市场价格失败", strategy.name)
        return

    trading_engine.save_price_to_db(db, strategy.symbol, current_price)

    positions = (
        db.query(Position)
        .filter(
            Position.user_id == user.id,
            Position.symbol == strategy.symbol,
            Position.is_open.is_(True),
        )
        .all()
    )
    position_data = [
        {
            "id": position.id,
            "symbol": position.symbol,
            "side": position.side.value,
            "entry_price": position.entry_price,
            "quantity": position.quantity,
            "leverage": position.leverage,
            "margin": position.margin,
            "unrealized_pnl": position.unrealized_pnl,
            "liquidation_price": position.liquidation_price,
        }
        for position in positions
    ]

    history_snapshot = build_strategy_history_snapshot(db, strategy)
    history_context = format_strategy_history_context(history_snapshot)
    effective_prompt_text = await maybe_optimize_strategy_prompt(db, strategy, user, history_snapshot)

    indicators = (market_data or {}).get("indicators", {})
    ohlcv = (market_data or {}).get("ohlcv", {})
    closes = ohlcv.get("closes", [])[-10:]
    timestamps = ohlcv.get("timestamps", [])[-10:]
    price_data = [
        {"timestamp": str(timestamp), "price": price}
        for timestamp, price in zip(timestamps, closes)
    ]

    total_position_value = sum((position.margin or 0) + (position.unrealized_pnl or 0) for position in positions)
    total_assets = user.balance + total_position_value
    roi = ((total_assets - user.initial_balance) / user.initial_balance * 100) if user.initial_balance else 0.0

    market_analysis = f"""# {strategy.symbol} 市场分析

## 技术指标
{json.dumps(indicators, ensure_ascii=False, indent=2)}

## 最近价格
{format_price_history(price_data)}

## 当前持仓
{format_positions(position_data)}

## 账户状态
- 总资产: ${total_assets:,.2f}
- 总收益率(ROI): {roi:.2f}%
- 初始资金: ${user.initial_balance:,.2f}
- 当前余额: ${user.balance:,.2f}
- 持仓价值: ${total_position_value:,.2f}
- 手续费率: {user.trading_fee_rate:.4%}
- 爆仓阈值: {user.liquidation_threshold:.2%}

{history_context}"""

    market_context = json.dumps(
        {
            "price": current_price,
            "indicators": indicators,
            "positions": position_data,
            "balance": user.balance,
            "total_assets": total_assets,
            "roi": roi,
            "initial_balance": user.initial_balance,
            "history_snapshot": history_snapshot,
        },
        ensure_ascii=False,
    )

    messages = [
        {"role": "system", "content": effective_prompt_text},
        {
            "role": "user",
            "content": f"""{market_analysis}

请基于以上市场上下文做出本轮交易决策。

要求：
1. 先考虑已有持仓的风险管理，再考虑是否新开仓
2. 如果信号不足、收益空间不足或成本不划算，优先返回 hold
3. 必须只输出 JSON，不要输出额外解释

输出格式：
{{
  "action": "open/close/hold",
  "direction": "long/short",
  "quantity": 0.01,
  "leverage": 3,
  "reasoning": "简要说明"
}}

quantity 必须大于 0。
示例：若账户 10000 USDT，使用 10% 仓位和 3x 杠杆，BTC 价格 100000，则 quantity = (10000 * 0.1 * 3) / 100000 = 0.03""",
        },
    ]

    raw_content = ""
    reasoning = ""
    decision_text = "ERROR"
    action_taken = False

    try:
        result = await ai_service.chat_completion(
            messages=messages,
            api_key=user.ai_api_key,
            base_url=user.ai_base_url or "",
            model=user.ai_model or "claude-4.5-opus",
            temperature=0.7,
            max_tokens=1000,
        )
        raw_content = result["choices"][0]["message"]["content"]
        payload = json.loads(extract_json_from_content(raw_content))
        action = (payload.get("action") or "hold").lower()
        decision_text = action.upper()
        reasoning = payload.get("reasoning") or ""

        if action == "open":
            action_taken = await execute_open_position(db, user, strategy, payload, current_price, market_data or {})
        elif action == "close":
            action_taken = await execute_close_positions(db, user, strategy, positions, current_price, market_data or {})
        else:
            hold_trade = Trade(
                user_id=user.id,
                symbol=strategy.symbol,
                side=TradeSide.BUY,
                price=current_price,
                quantity=0,
                leverage=max(int(payload.get("leverage") or 1), 1),
                execution_source="AI",
                trade_type=TradeType.HOLD,
                market_data=json.dumps(
                    {
                        "decision": "HOLD",
                        "reasoning": reasoning,
                        "price": current_price,
                        "indicators": indicators,
                    },
                    ensure_ascii=False,
                ),
            )
            db.add(hold_trade)
            db.commit()
    except AIAPIError as exc:
        raw_content = str(exc)
        reasoning = raw_content
        error_trade = Trade(
            user_id=user.id,
            symbol=strategy.symbol,
            side=TradeSide.BUY,
            price=current_price,
            quantity=0,
            leverage=1,
            execution_source="AI",
            trade_type=TradeType.ERROR,
            market_data=json.dumps(
                {
                    "error": raw_content,
                    "error_type": "api_error",
                    "status_code": exc.status_code,
                    "api_response": exc.response_body,
                    "price": current_price,
                    "indicators": indicators,
                },
                ensure_ascii=False,
            ),
        )
        db.add(error_trade)
        db.commit()
    except Exception as exc:
        raw_content = str(exc)
        reasoning = raw_content
        error_trade = Trade(
            user_id=user.id,
            symbol=strategy.symbol,
            side=TradeSide.BUY,
            price=current_price,
            quantity=0,
            leverage=1,
            execution_source="AI",
            trade_type=TradeType.ERROR,
            market_data=json.dumps(
                {
                    "error": raw_content,
                    "error_type": "executor_error",
                    "price": current_price,
                    "indicators": indicators,
                },
                ensure_ascii=False,
            ),
        )
        db.add(error_trade)
        db.commit()
    finally:
        db.add(
            AIDecisionLog(
                user_id=user.id,
                prompt_name=strategy.name,
                market_context=market_context,
                ai_reasoning=reasoning or raw_content,
                decision=decision_text,
                action_taken=action_taken,
            )
        )
        strategy.last_executed_at = get_local_time()
        db.commit()


async def execute_open_position(
    db: Session,
    user: User,
    strategy: PromptConfig,
    decision: dict,
    current_price: float,
    market_data: dict | None = None,
) -> bool:
    direction = (decision.get("direction") or "long").lower()
    quantity = float(decision.get("quantity") or 0)
    leverage = max(int(decision.get("leverage") or 1), 1)
    if quantity <= 0:
        return False

    position_side = TradeSide.LONG if direction == "long" else TradeSide.SHORT
    notional_value = calculate_notional_value(current_price, quantity)
    fee_paid = calculate_fee(current_price, quantity, user.trading_fee_rate)
    margin = notional_value / leverage
    total_cost = margin + fee_paid
    if user.balance < total_cost:
        return False

    balance_before = user.balance
    user.balance -= total_cost
    user.updated_at = get_local_time()
    liquidation_price = calculate_liquidation_price(
        current_price,
        leverage,
        position_side,
        user.liquidation_threshold,
    )

    position = Position(
        user_id=user.id,
        symbol=strategy.symbol,
        side=position_side,
        entry_price=current_price,
        quantity=quantity,
        leverage=leverage,
        margin=margin,
        liquidation_price=liquidation_price,
    )
    db.add(position)
    db.flush()

    trade = Trade(
        user_id=user.id,
        position_id=position.id,
        symbol=strategy.symbol,
        side=TradeSide.BUY if position_side == TradeSide.LONG else TradeSide.SELL,
        position_side=position_side,
        price=current_price,
        quantity=quantity,
        leverage=leverage,
        margin_used=margin,
        notional_value=notional_value,
        fee_paid=fee_paid,
        balance_before=balance_before,
        balance_after=user.balance,
        roi_pct=calculate_roi_pct(0.0, margin),
        entry_price_snapshot=current_price,
        liquidation_price_snapshot=liquidation_price,
        close_reason="AI_OPEN",
        execution_source="AI",
        trade_type=TradeType.OPEN,
        market_data=json.dumps(
            {
                "reasoning": decision.get("reasoning") or "",
                "fee_rate": user.trading_fee_rate,
                "estimated_total_cost": round(total_cost, 8),
                "indicators": (market_data or {}).get("indicators", {}),
            },
            ensure_ascii=False,
        ),
    )
    db.add(trade)
    db.commit()
    return True


async def execute_close_positions(
    db: Session,
    user: User,
    strategy: PromptConfig,
    positions: list,
    current_price: float,
    market_data: dict | None = None,
) -> bool:
    if not positions:
        trade = Trade(
            user_id=user.id,
            symbol=strategy.symbol,
            side=TradeSide.BUY,
            price=current_price,
            quantity=0,
            leverage=1,
            execution_source="AI",
            trade_type=TradeType.HOLD,
            market_data=json.dumps(
                {
                    "decision": "HOLD",
                    "reasoning": "无有效决策，已忽略本次执行",
                    "price": current_price,
                    "indicators": (market_data or {}).get("indicators", {}),
                },
                ensure_ascii=False,
            ),
        )
        db.add(trade)
        db.commit()
        return False

    for position in positions:
        if position.side == TradeSide.LONG:
            pnl = (current_price - position.entry_price) * position.quantity
        else:
            pnl = (position.entry_price - current_price) * position.quantity

        notional_value = calculate_notional_value(current_price, position.quantity)
        fee_paid = calculate_fee(current_price, position.quantity, user.trading_fee_rate)
        balance_before = user.balance
        closed_at = get_local_time()

        user.balance += position.margin + pnl - fee_paid
        user.updated_at = closed_at
        position.is_open = False
        position.closed_at = closed_at
        position.unrealized_pnl = pnl

        trade = Trade(
            user_id=user.id,
            position_id=position.id,
            symbol=position.symbol,
            side=TradeSide.SELL if position.side == TradeSide.LONG else TradeSide.BUY,
            position_side=position.side,
            price=current_price,
            quantity=position.quantity,
            leverage=position.leverage,
            margin_used=position.margin,
            notional_value=notional_value,
            pnl=pnl,
            fee_paid=fee_paid,
            balance_before=balance_before,
            balance_after=user.balance,
            roi_pct=calculate_roi_pct(pnl, position.margin),
            holding_seconds=calculate_holding_seconds(position.created_at, closed_at),
            entry_price_snapshot=position.entry_price,
            liquidation_price_snapshot=position.liquidation_price,
            close_reason="AI_CLOSE",
            execution_source="AI",
            trade_type=TradeType.CLOSE,
            market_data=json.dumps(
                {
                    "exit_price": round(current_price, 8),
                    "fee_rate": user.trading_fee_rate,
                    "close_reason": "AI_CLOSE",
                    "indicators": (market_data or {}).get("indicators", {}),
                },
                ensure_ascii=False,
            ),
        )
        db.add(trade)

    db.commit()
    return True


