"""
策略执行定时任务
"""
import logging
import re
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from backend.core.database import SessionLocal
from backend.core.models import PromptConfig, User, Position, MarketPrice, Trade, TradeSide, TradeType, get_local_time
from backend.services.ai_service import ai_service

logger = logging.getLogger(__name__)


async def execute_active_strategies():
    """
    执行所有激活的策略
    检查每个策略的执行间隔，如果到时间则执行
    """
    # 快速获取需要执行的策略ID列表，然后立即释放连接
    db = SessionLocal()
    try:
        active_strategies = db.query(PromptConfig).filter(
            PromptConfig.is_active == True
        ).all()

        # 提取需要执行的策略信息
        strategies_to_execute = [
            {"id": s.id, "name": s.name, "symbol": s.symbol}
            for s in active_strategies
            if should_execute_strategy(s)
        ]

        logger.debug(f"发现 {len(active_strategies)} 个激活的策略，{len(strategies_to_execute)} 个需要执行")
    except Exception as e:
        logger.error(
            f"获取策略列表失败:\n"
            f"  错误类型: {type(e).__name__}\n"
            f"  错误信息: {str(e)}",
            exc_info=True
        )
        return
    finally:
        db.close()

    # 为每个策略创建独立的数据库会话
    for strategy_info in strategies_to_execute:
        db = SessionLocal()
        try:
            # 重新查询策略对象（使用新的会话）
            strategy = db.query(PromptConfig).filter(
                PromptConfig.id == strategy_info["id"]
            ).first()

            if strategy:
                logger.info(f"执行策略: {strategy.name} ({strategy.symbol})")
                await execute_single_strategy(db, strategy)
            else:
                logger.warning(f"策略 ID {strategy_info['id']} 不存在")
        except Exception as e:
            logger.error(
                f"执行策略 {strategy_info['name']} 失败:\n"
                f"  错误类型: {type(e).__name__}\n"
                f"  错误信息: {str(e)}",
                exc_info=True
            )
            db.rollback()
        finally:
            db.close()


def should_execute_strategy(strategy: PromptConfig) -> bool:
    """
    判断策略是否应该执行

    Args:
        strategy: 策略对象

    Returns:
        是否应该执行
    """
    # 如果从未执行过，立即执行
    if strategy.last_executed_at is None:
        return True

    # 计算距离上次执行的时间（秒）
    # 确保使用本地时区时间进行比较
    now = get_local_time()
    # 如果 last_executed_at 带有时区信息，去掉时区信息（因为已经是本地时间）
    if strategy.last_executed_at.tzinfo is not None:
        last_executed = strategy.last_executed_at.replace(tzinfo=None)
    else:
        last_executed = strategy.last_executed_at

    elapsed = (now - last_executed).total_seconds()

    # execution_interval 现在是分钟，需要转换为秒
    interval_seconds = strategy.execution_interval * 60

    # 如果超过执行间隔，则执行
    return elapsed >= interval_seconds


async def execute_single_strategy(db: Session, strategy: PromptConfig):
    """
    执行单个策略

    Args:
        db: 数据库会话
        strategy: 策略对象
    """
    import json
    from backend.core.models import AIDecisionLog

    error_message = None
    market_context = None
    ai_reasoning = None
    decision_action = "HOLD"
    action_taken = False

    try:
        # 获取用户信息
        user = db.query(User).filter(User.id == strategy.user_id).first()
        if not user:
            error_message = f"策略 {strategy.name} 的用户不存在"
            logger.error(error_message)
            return

        # 获取市场数据（包含技术指标）
        from backend.engine.engine import trading_engine
        market_data = trading_engine.fetch_market_data(
            symbol=strategy.symbol,
            timeframe='1h',
            limit=100
        )

        if not market_data:
            error_message = f"无法获取 {strategy.symbol} 的市场数据"
            logger.warning(error_message)
            # 记录错误到交易历史
            trade = Trade(
                user_id=user.id,
                symbol=strategy.symbol,
                side=TradeSide.BUY,
                price=0,
                quantity=0,
                leverage=1,
                trade_type=TradeType.ERROR,
                market_data=json.dumps({"error": error_message})
            )
            db.add(trade)
            db.commit()
            return

        current_price = market_data['current_price']
        indicators = market_data['indicators']

        # 获取历史价格
        price_history = (
            db.query(MarketPrice)
            .filter(MarketPrice.symbol == strategy.symbol)
            .order_by(MarketPrice.timestamp.desc())
            .limit(50)
            .all()
        )

        # 获取用户在该交易对的持仓
        positions = (
            db.query(Position)
            .filter(
                Position.user_id == strategy.user_id,
                Position.symbol == strategy.symbol,
                Position.is_open == True
            )
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

        # 计算总资产和收益率
        all_positions = (
            db.query(Position)
            .filter(
                Position.user_id == strategy.user_id,
                Position.is_open == True
            )
            .all()
        )
        total_position_value = sum(p.margin + p.unrealized_pnl for p in all_positions)
        total_assets = user.balance + total_position_value
        roi = ((total_assets - user.initial_balance) / user.initial_balance) * 100 if user.initial_balance > 0 else 0

        # 构建市场分析信息（优化版本，充分利用市场数据）
        market_analysis = f"""# {strategy.symbol} 市场分析报告

## 当前市场状态
- **当前价格**: ${current_price:,.2f}
- **24h涨跌**: {indicators.get('price_change_pct', 0):.2f}%
- **成交量变化**: {indicators.get('vol_ratio', 1):.2f}x (相对于平均成交量)

## 技术指标分析
### 移动平均线 (MA)
- **MA5** (短期趋势): ${indicators.get('ma5', 0):,.2f}
- **MA10** (中期趋势): ${indicators.get('ma10', 0):,.2f}
- **MA30** (长期趋势): ${indicators.get('ma30', 0):,.2f}
- **均线排列**: {"多头排列" if indicators.get('ma5', 0) > indicators.get('ma10', 0) > indicators.get('ma30', 0) else "空头排列" if indicators.get('ma5', 0) < indicators.get('ma10', 0) < indicators.get('ma30', 0) else "震荡"}

### 相对强弱指标 (RSI)
- **RSI**: {indicators.get('rsi', 50):.2f}
- **市场状态**: {"超买区 (>70)" if indicators.get('rsi', 50) > 70 else "超卖区 (<30)" if indicators.get('rsi', 50) < 30 else "正常区间 (30-70)"}

### MACD 指标
- **MACD**: {indicators.get('macd', 0):.2f}
- **信号线**: {indicators.get('macd_signal', 0):.2f}
- **柱状图**: {indicators.get('macd_hist', 0):.2f}
- **趋势信号**: {"金叉 (看涨)" if indicators.get('macd_hist', 0) > 0 else "死叉 (看跌)"}

### 布林带 (Bollinger Bands)
- **上轨**: ${indicators.get('bb_upper', 0):,.2f}
- **中轨**: ${indicators.get('bb_middle', 0):,.2f}
- **下轨**: ${indicators.get('bb_lower', 0):,.2f}
- **位置**: {"接近上轨" if current_price > indicators.get('bb_middle', 0) else "接近下轨"}

## 最近价格走势
{format_price_history(price_data[-10:])}

## 当前持仓情况
{format_positions(position_data)}

## 账户状态
- **总资产**: ${total_assets:,.2f}
- **收益率 (ROI)**: {roi:.2f}%
- **初始资金**: ${user.initial_balance:,.2f}
- **可用余额**: ${user.balance:,.2f}
- **持仓价值**: ${total_position_value:,.2f}
- **持仓数量**: {len(position_data)}
- **最大可开仓**: ${user.balance * 10:,.2f} (最高10x杠杆，由AI决定)"""

        # 保存市场上下文
        market_context = json.dumps({
            "price": current_price,
            "indicators": indicators,
            "positions": position_data,
            "balance": user.balance,
            "total_assets": total_assets,
            "roi": roi,
            "initial_balance": user.initial_balance
        })

        # 使用自定义提示词进行分析
        messages = [
            {
                "role": "system",
                "content": strategy.prompt_text
            },
            {
                "role": "user",
                "content": f"""{market_analysis}

请基于上述完整的市场数据进行深入分析，并给出精准的交易建议。

**要求**:
1. 综合考虑所有技术指标（MA、RSI、MACD、布林带）
2. 分析当前市场趋势和动量
3. 评估风险收益比
4. 给出具体的交易参数
5. 根据市场波动性和风险评估自行决定合适的杠杆倍数（1-20x）

**返回JSON格式**:
{{
    "action": "open/close/hold",
    "direction": "long/short",
    "quantity": 0.01,
    "leverage": 3,
    "reasoning": "详细的决策理由，包括技术分析依据和杠杆选择理由"
}}

**重要**: quantity 必须大于 0！请根据可用余额和当前价格计算合理的开仓数量。
计算公式参考: quantity = (可用余额 * 仓位比例 * 杠杆) / 当前价格
例如余额 10000 USDT，使用 10% 仓位，3x 杠杆，BTC 价格 100000: quantity = (10000 * 0.1 * 3) / 100000 = 0.03"""
            }
        ]

        # 调用 AI（需要用户的 API 配置）
        if not user.ai_api_key:
            error_message = f"用户 {user.username} 未配置 API Key"
            logger.warning(error_message)
            # 记录错误
            trade = Trade(
                user_id=user.id,
                symbol=strategy.symbol,
                side=TradeSide.BUY,
                price=current_price,
                quantity=0,
                leverage=1,
                trade_type=TradeType.ERROR,
                market_data=json.dumps({
                    "error": error_message,
                    "price": current_price,
                    "indicators": indicators
                })
            )
            db.add(trade)
            db.commit()
            return

        result = await ai_service.chat_completion(
            messages=messages,
            api_key=user.ai_api_key,
            base_url=user.ai_base_url or "",
            model=user.ai_model or "claude-4.5-opus",
            temperature=0.7,
            max_tokens=1000
        )

        content = result["choices"][0]["message"]["content"]

        # 解析 AI 响应
        try:
            decision = json.loads(extract_json_from_content(content))
            ai_reasoning = decision.get("reasoning", "")
            decision_action = decision.get("action", "hold").upper()

            logger.debug(f"策略 {strategy.name} AI 决策: {decision}")

            # 执行交易决策（传递市场数据用于记录）
            action = decision.get("action", "hold").lower()

            if action == "open":
                # 开仓
                success = await execute_open_position(db, user, strategy, decision, current_price, market_data)
                action_taken = success
            elif action == "close":
                # 平仓
                success = await execute_close_positions(db, user, strategy, positions, current_price, market_data)
                action_taken = success
            elif action == "hold":
                logger.debug(f"策略 {strategy.name} 决策: 持有，不操作")
                trade = Trade(
                    user_id=user.id,
                    symbol=strategy.symbol,
                    side=TradeSide.BUY,
                    price=current_price,
                    quantity=0,
                    leverage=1,
                    trade_type=TradeType.HOLD,
                    market_data=json.dumps({
                        "decision": "HOLD",
                        "reasoning": ai_reasoning,
                        "price": current_price,
                        "indicators": indicators
                    })
                )
                db.add(trade)
            else:
                error_message = f"未知操作: {action}"
                logger.warning(f"策略 {strategy.name} {error_message}")
                # 记录错误
                trade = Trade(
                    user_id=user.id,
                    symbol=strategy.symbol,
                    side=TradeSide.BUY,
                    price=current_price,
                    quantity=0,
                    leverage=1,
                    trade_type=TradeType.ERROR,
                    market_data=json.dumps({
                        "error": error_message,
                        "price": current_price,
                        "indicators": indicators
                    })
                )
                db.add(trade)

        except json.JSONDecodeError as e:
            error_message = f"AI响应无法解析为JSON: {content}"
            logger.warning(f"策略 {strategy.name} {error_message}")
            ai_reasoning = content
            decision_action = "ERROR"

            # 记录解析错误到交易历史
            trade = Trade(
                user_id=user.id,
                symbol=strategy.symbol,
                side=TradeSide.BUY,
                price=current_price,
                quantity=0,
                leverage=1,
                trade_type=TradeType.ERROR,
                market_data=json.dumps({
                    "error": error_message,
                    "ai_response": content,
                    "price": current_price,
                    "indicators": indicators
                })
            )
            db.add(trade)

        # 记录AI决策日志
        decision_log = AIDecisionLog(
            user_id=user.id,
            prompt_name=strategy.name,
            market_context=market_context,
            ai_reasoning=ai_reasoning,
            decision=decision_action,
            action_taken=action_taken
        )
        db.add(decision_log)

        # 更新最后执行时间
        strategy.last_executed_at = get_local_time()
        db.commit()

    except Exception as e:
        error_message = f"执行策略失败: {str(e)}"
        logger.error(
            f"策略 {strategy.name if strategy else 'Unknown'} {error_message}\n"
            f"  错误类型: {type(e).__name__}\n"
            f"  策略ID: {strategy.id if strategy else 'N/A'}\n"
            f"  用户ID: {strategy.user_id if strategy else 'N/A'}",
            exc_info=True
        )

        db.rollback()

        # 记录异常到交易历史和决策日志
        try:
            if user and strategy:
                # 尝试获取当前价格
                error_price = current_price if 'current_price' in dir() else 0

                trade = Trade(
                    user_id=user.id,
                    symbol=strategy.symbol,
                    side=TradeSide.BUY,
                    price=error_price,
                    quantity=0,
                    leverage=1,
                    trade_type=TradeType.ERROR,
                    market_data=json.dumps({
                        "error": error_message,
                        "exception": str(e)
                    })
                )
                db.add(trade)

                decision_log = AIDecisionLog(
                    user_id=user.id,
                    prompt_name=strategy.name,
                    market_context=market_context or "{}",
                    ai_reasoning=error_message,
                    decision="ERROR",
                    action_taken=False
                )
                db.add(decision_log)

                # 更新最后执行时间（避免错误时反复重试）
                strategy.last_executed_at = get_local_time()

                db.commit()
        except Exception:
            db.rollback()


def extract_json_from_content(content: str) -> str:
    """从 AI 响应中提取 JSON，支持 markdown 代码块包裹的情况"""
    # 尝试提取 ```json ... ``` 或 ``` ... ``` 块
    match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
    if match:
        return match.group(1)
    # 尝试直接找第一个 { ... } 块
    match = re.search(r'\{.*\}', content, re.DOTALL)
    if match:
        return match.group(0)
    return content


def format_price_history(history: list) -> str:
    """格式化价格历史"""
    if not history:
        return "无历史数据"

    lines = []
    for item in history:
        price = item.get('price', 0)
        timestamp = item.get('timestamp', '')
        lines.append(f"  {timestamp}: ${price:,.2f}")

    return "\n".join(lines)


def format_positions(positions: list) -> str:
    """格式化持仓信息"""
    if not positions:
        return "无持仓"

    lines = []
    for pos in positions:
        side = pos.get('side', '')
        quantity = pos.get('quantity', 0)
        entry_price = pos.get('entry_price', 0)
        pnl = pos.get('unrealized_pnl', 0)
        lines.append(
            f"  {side} {quantity} @ ${entry_price:,.2f} (盈亏: ${pnl:,.2f})"
        )

    return "\n".join(lines)


async def execute_open_position(db: Session, user: User, strategy: PromptConfig, decision: dict, current_price: float, market_data: dict = None) -> bool:
    """
    执行开仓操作

    Args:
        db: 数据库会话
        user: 用户对象
        strategy: 策略对象
        decision: AI决策
        current_price: 当前价格
        market_data: 市场数据快照

    Returns:
        是否开仓成功
    """
    import json

    try:
        direction = decision.get("direction", "long").lower()
        quantity = float(decision.get("quantity", 0))
        leverage = int(decision.get("leverage", 3))
        reasoning = decision.get("reasoning", "")

        # 如果 AI 返回的数量为 0 或负数，根据余额自动计算合理数量
        if quantity <= 0:
            # 默认使用 10% 的余额开仓
            leverage = max(leverage, 1)
            quantity = (user.balance * 0.1 * leverage) / current_price if current_price > 0 else 0.001
            quantity = round(quantity, 6)
            logger.debug(f"策略 {strategy.name}: AI 返回数量为 0，自动计算数量为 {quantity}")

        # 确保最小数量
        if quantity < 0.00001:
            quantity = 0.00001

        # 转换方向
        side = TradeSide.LONG if direction == "long" else TradeSide.SHORT

        # 计算保证金
        margin = (current_price * quantity) / leverage

        # 检查余额是否足够
        if user.balance < margin:
            error_msg = f"余额不足 (需要 ${margin:.2f}, 可用 ${user.balance:.2f})"
            logger.warning(f"策略 {strategy.name} 开仓失败: {error_msg}")

            # 记录失败到交易历史
            market_data_json = json.dumps({
                'error': error_msg,
                'price': current_price,
                'indicators': market_data.get('indicators', {}) if market_data else {},
                'decision': decision
            })

            trade = Trade(
                user_id=user.id,
                symbol=strategy.symbol,
                side=TradeSide.BUY if side == TradeSide.LONG else TradeSide.SELL,
                price=current_price,
                quantity=quantity,
                leverage=leverage,
                trade_type=TradeType.OPEN,
                market_data=market_data_json
            )
            db.add(trade)
            db.commit()
            return False

        # 扣除保证金
        user.balance -= margin
        user.updated_at = get_local_time()

        # 创建持仓
        new_position = Position(
            user_id=user.id,
            symbol=strategy.symbol,
            side=side,
            entry_price=current_price,
            quantity=quantity,
            leverage=leverage,
            margin=margin,
        )
        db.add(new_position)

        # 创建交易记录时，保存完整市场数据
        market_data_json = json.dumps({
            'price': current_price,
            'indicators': market_data.get('indicators', {}) if market_data else {},
            'timestamp': market_data.get('timestamp') if market_data else str(get_local_time()),
            'decision': decision,
            'reasoning': reasoning
        })

        # 记录交易历史
        trade = Trade(
            user_id=user.id,
            symbol=strategy.symbol,
            side=TradeSide.BUY if side == TradeSide.LONG else TradeSide.SELL,
            price=current_price,
            quantity=quantity,
            leverage=leverage,
            trade_type=TradeType.OPEN,
            market_data=market_data_json
        )
        db.add(trade)

        db.commit()

        logger.info(
            f"策略 {strategy.name} 开仓成功: {side.value} {quantity} {strategy.symbol} @ ${current_price:.2f} {leverage}x | 理由: {reasoning[:100]}"
        )
        return True

    except Exception as e:
        error_msg = f"开仓异常: {str(e)}"
        logger.error(
            f"策略 {strategy.name} {error_msg}\n"
            f"  错误类型: {type(e).__name__}\n"
            f"  决策: {decision}",
            exc_info=True
        )

        # 记录异常到交易历史
        try:
            market_data_json = json.dumps({
                'error': error_msg,
                'exception': str(e),
                'price': current_price,
                'decision': decision
            })

            trade = Trade(
                user_id=user.id,
                symbol=strategy.symbol,
                side=TradeSide.BUY,
                price=current_price,
                quantity=0,
                leverage=1,
                trade_type=TradeType.OPEN,
                market_data=market_data_json
            )
            db.add(trade)
            db.commit()
        except:
            pass

        db.rollback()
        return False


async def execute_close_positions(db: Session, user: User, strategy: PromptConfig, positions: list, current_price: float, market_data: dict = None) -> bool:
    """
    执行平仓操作

    Args:
        db: 数据库会话
        user: 用户对象
        strategy: 策略对象
        positions: 持仓列表
        current_price: 当前价格
        market_data: 市场数据快照

    Returns:
        是否平仓成功
    """
    import json

    try:
        if not positions:
            logger.debug(f"策略 {strategy.name} 无持仓可平")
            # 记录无持仓到交易历史
            market_data_json = json.dumps({
                'info': '无持仓可平',
                'price': current_price,
                'indicators': market_data.get('indicators', {}) if market_data else {}
            })

            trade = Trade(
                user_id=user.id,
                symbol=strategy.symbol,
                side=TradeSide.SELL,
                price=current_price,
                quantity=0,
                leverage=1,
                trade_type=TradeType.CLOSE,
                market_data=market_data_json
            )
            db.add(trade)
            db.commit()
            return False

        total_pnl = 0

        for position in positions:
            # 计算盈亏
            if position.side == TradeSide.LONG:
                pnl = (current_price - position.entry_price) * position.quantity * position.leverage
            else:
                pnl = (position.entry_price - current_price) * position.quantity * position.leverage

            # 退还保证金 + 盈亏
            user.balance += position.margin + pnl
            user.updated_at = get_local_time()

            # 更新持仓状态
            position.is_open = False
            position.closed_at = get_local_time()
            position.unrealized_pnl = pnl

            # 创建交易记录时，保存完整市场数据
            market_data_json = json.dumps({
                'price': current_price,
                'indicators': market_data.get('indicators', {}) if market_data else {},
                'timestamp': market_data.get('timestamp') if market_data else str(get_local_time()),
                'position': {
                    'side': position.side.value,
                    'entry_price': position.entry_price,
                    'quantity': position.quantity,
                    'leverage': position.leverage
                },
                'pnl': pnl
            })

            # 记录交易历史
            trade = Trade(
                user_id=user.id,
                symbol=strategy.symbol,
                side=TradeSide.SELL if position.side == TradeSide.LONG else TradeSide.BUY,
                price=current_price,
                quantity=position.quantity,
                leverage=position.leverage,
                pnl=pnl,
                trade_type=TradeType.CLOSE,
                market_data=market_data_json
            )
            db.add(trade)

            total_pnl += pnl

            logger.info(
                f"策略 {strategy.name} 平仓: {position.side.value} {position.quantity} {strategy.symbol} @ ${current_price:.2f} 盈亏 ${pnl:.2f}"
            )

        db.commit()

        logger.info(f"策略 {strategy.name} 平仓完成，总盈亏: ${total_pnl:.2f}")
        return True

    except Exception as e:
        error_msg = f"平仓异常: {str(e)}"
        logger.error(
            f"策略 {strategy.name} {error_msg}\n"
            f"  错误类型: {type(e).__name__}\n"
            f"  决策: {decision}",
            exc_info=True
        )

        # 记录异常到交易历史
        try:
            market_data_json = json.dumps({
                'error': error_msg,
                'exception': str(e),
                'price': current_price
            })

            trade = Trade(
                user_id=user.id,
                symbol=strategy.symbol,
                side=TradeSide.SELL,
                price=current_price,
                quantity=0,
                leverage=1,
                trade_type=TradeType.CLOSE,
                market_data=market_data_json
            )
            db.add(trade)
            db.commit()
        except:
            pass

        db.rollback()
        return False

