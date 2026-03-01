"""
交易引擎 - CCXT 行情获取 + AI 决策逻辑
"""
import ccxt
import logging
from datetime import datetime
from typing import Dict, Optional, List
from sqlalchemy.orm import Session
from backend.core.models import (
    MarketPrice,
    Position,
    User,
    PromptConfig,
    Trade,
    TradeSide,
    TradeType,
    AIDecisionLog,
    AIConversation,
    get_local_time,
)
from backend.core.config import settings

logger = logging.getLogger(__name__)


class TradingEngine:
    """交易引擎类"""

    def __init__(self):
        self.exchange = None
        self._init_exchange()

    def _init_exchange(self):
        """初始化交易所连接"""
        try:
            exchange_class = getattr(ccxt, settings.EXCHANGE)
            self.exchange = exchange_class(
                {
                    "enableRateLimit": True,
                }
            )
            logger.info(f"成功连接到交易所: {settings.EXCHANGE}")
        except Exception as e:
            logger.error(f"交易所初始化失败: {e}")

    def fetch_current_price(self, symbol: str = None) -> Optional[float]:
        """
        获取当前市场价格

        Args:
            symbol: 交易对，默认使用配置文件中的 TRADING_PAIR

        Returns:
            当前价格，失败返回 None
        """
        if not self.exchange:
            self._init_exchange()

        symbol = symbol or settings.TRADING_PAIR

        try:
            ticker = self.exchange.fetch_ticker(symbol)
            price = ticker["last"]
            logger.debug(f"{symbol} 当前价格: {price}")
            return price
        except Exception as e:
            logger.error(f"获取价格失败 ({symbol}): {e}")
            return None

    def fetch_market_data(self, symbol: str = None, timeframe: str = '1h', limit: int = 100) -> Optional[Dict]:
        """
        获取市场数据，包括K线和技术指标

        Args:
            symbol: 交易对
            timeframe: 时间周期 (1m, 5m, 15m, 1h, 4h, 1d)
            limit: 获取的K线数量

        Returns:
            包含价格、成交量和技术指标的字典
        """
        if not self.exchange:
            self._init_exchange()

        symbol = symbol or settings.TRADING_PAIR

        try:
            # 获取OHLCV数据
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)

            # 解析数据
            timestamps = [x[0] for x in ohlcv]
            opens = [x[1] for x in ohlcv]
            highs = [x[2] for x in ohlcv]
            lows = [x[3] for x in ohlcv]
            closes = [x[4] for x in ohlcv]
            volumes = [x[5] for x in ohlcv]

            # 计算技术指标
            indicators = self._calculate_indicators(closes, volumes)

            return {
                'symbol': symbol,
                'timeframe': timeframe,
                'timestamp': timestamps[-1],
                'current_price': closes[-1],
                'open': opens[-1],
                'high': highs[-1],
                'low': lows[-1],
                'volume': volumes[-1],
                'ohlcv': {
                    'timestamps': timestamps,
                    'opens': opens,
                    'highs': highs,
                    'lows': lows,
                    'closes': closes,
                    'volumes': volumes
                },
                'indicators': indicators
            }
        except Exception as e:
            logger.error(f"获取市场数据失败 ({symbol}): {e}")
            return None

    def _calculate_indicators(self, closes: List[float], volumes: List[float]) -> Dict:
        """
        计算技术指标

        Args:
            closes: 收盘价列表
            volumes: 成交量列表

        Returns:
            技术指标字典
        """
        indicators = {}

        # MA5 - 5日移动平均线
        if len(closes) >= 5:
            indicators['ma5'] = sum(closes[-5:]) / 5
        else:
            indicators['ma5'] = None

        # MA10 - 10日移动平均线
        if len(closes) >= 10:
            indicators['ma10'] = sum(closes[-10:]) / 10
        else:
            indicators['ma10'] = None

        # MA30 - 30日移动平均线
        if len(closes) >= 30:
            indicators['ma30'] = sum(closes[-30:]) / 30
        else:
            indicators['ma30'] = None

        # 成交量移动平均
        if len(volumes) >= 10:
            indicators['vol_ma10'] = sum(volumes[-10:]) / 10
        else:
            indicators['vol_ma10'] = None

        # 当前成交量与平均成交量的比率
        if indicators['vol_ma10']:
            indicators['vol_ratio'] = volumes[-1] / indicators['vol_ma10']
        else:
            indicators['vol_ratio'] = None

        # 价格变化率
        if len(closes) >= 2:
            indicators['price_change_pct'] = ((closes[-1] - closes[-2]) / closes[-2]) * 100
        else:
            indicators['price_change_pct'] = None

        # RSI (简化版本 - 14周期)
        if len(closes) >= 15:
            indicators['rsi'] = self._calculate_rsi(closes, period=14)
        else:
            indicators['rsi'] = None

        # MACD (12, 26, 9)
        macd_data = self._calculate_macd(closes)
        indicators['macd'] = macd_data['macd']
        indicators['macd_signal'] = macd_data['signal']
        indicators['macd_hist'] = macd_data['histogram']

        # 布林带 (20, 2)
        bb_data = self._calculate_bollinger_bands(closes)
        indicators['bb_upper'] = bb_data['upper']
        indicators['bb_middle'] = bb_data['middle']
        indicators['bb_lower'] = bb_data['lower']

        return indicators

    def _calculate_rsi(self, prices: List[float], period: int = 14) -> Optional[float]:
        """
        计算RSI指标

        Args:
            prices: 价格列表
            period: 周期

        Returns:
            RSI值 (0-100)
        """
        if len(prices) < period + 1:
            return None

        # 计算价格变化
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]

        # 分离涨跌
        gains = [d if d > 0 else 0 for d in deltas[-period:]]
        losses = [-d if d < 0 else 0 for d in deltas[-period:]]

        # 计算平均涨跌
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period

        if avg_loss == 0:
            return 100

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return round(rsi, 2)

    def _calculate_macd(self, prices: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Dict:
        """
        计算MACD指标

        Args:
            prices: 价格列表
            fast: 快线周期
            slow: 慢线周期
            signal: 信号线周期

        Returns:
            {'macd': float, 'signal': float, 'histogram': float}
        """
        if len(prices) < slow + signal:
            return {'macd': None, 'signal': None, 'histogram': None}

        # 计算EMA
        def ema(data, period):
            if len(data) < period:
                return None
            multiplier = 2 / (period + 1)
            ema_values = [sum(data[:period]) / period]
            for price in data[period:]:
                ema_values.append((price - ema_values[-1]) * multiplier + ema_values[-1])
            return ema_values[-1]

        fast_ema = ema(prices, fast)
        slow_ema = ema(prices, slow)

        if fast_ema is None or slow_ema is None:
            return {'macd': None, 'signal': None, 'histogram': None}

        macd_line = fast_ema - slow_ema

        # 计算信号线 (MACD的EMA)
        # 简化版：使用最近的MACD值
        macd_values = []
        for i in range(max(slow, len(prices) - 50), len(prices)):
            f_ema = ema(prices[:i+1], fast)
            s_ema = ema(prices[:i+1], slow)
            if f_ema and s_ema:
                macd_values.append(f_ema - s_ema)

        if len(macd_values) >= signal:
            signal_line = ema(macd_values, signal)
        else:
            signal_line = macd_line

        histogram = macd_line - signal_line if signal_line else 0

        return {
            'macd': round(macd_line, 2),
            'signal': round(signal_line, 2) if signal_line else None,
            'histogram': round(histogram, 2)
        }

    def _calculate_bollinger_bands(self, prices: List[float], period: int = 20, std_dev: int = 2) -> Dict:
        """
        计算布林带指标

        Args:
            prices: 价格列表
            period: 周期
            std_dev: 标准差倍数

        Returns:
            {'upper': float, 'middle': float, 'lower': float}
        """
        if len(prices) < period:
            return {'upper': None, 'middle': None, 'lower': None}

        recent_prices = prices[-period:]
        middle = sum(recent_prices) / period

        # 计算标准差
        variance = sum((p - middle) ** 2 for p in recent_prices) / period
        std = variance ** 0.5

        upper = middle + (std_dev * std)
        lower = middle - (std_dev * std)

        return {
            'upper': round(upper, 2),
            'middle': round(middle, 2),
            'lower': round(lower, 2)
        }

    def fetch_multiple_prices(self, symbols: List[str]) -> Dict[str, Optional[float]]:
        """
        批量获取多个币种的价格

        Args:
            symbols: 交易对列表

        Returns:
            {symbol: price} 字典
        """
        if not self.exchange:
            self._init_exchange()

        prices = {}
        for symbol in symbols:
            try:
                ticker = self.exchange.fetch_ticker(symbol)
                prices[symbol] = ticker["last"]
            except Exception as e:
                logger.error(f"获取价格失败 ({symbol}): {e}")
                prices[symbol] = None

        return prices

    def save_price_to_db(self, db: Session, symbol: str, price: float):
        """
        保存价格到数据库

        Args:
            db: 数据库会话
            symbol: 交易对
            price: 价格
        """
        try:
            market_price = MarketPrice(symbol=symbol, price=price)
            db.add(market_price)
            db.commit()
            logger.debug(f"价格已保存: {symbol} = {price}")
        except Exception as e:
            logger.error(f"保存价格失败: {e}")
            db.rollback()

    def update_positions_pnl(self, db: Session, current_price: float, symbol: str = None):
        """
        更新指定交易对的所有持仓的未实现盈亏

        Args:
            db: 数据库会话
            current_price: 当前市场价格
            symbol: 交易对，如果为 None 则更新所有持仓
        """
        try:
            # 构建查询
            query = db.query(Position).filter(Position.is_open == True)
            if symbol:
                query = query.filter(Position.symbol == symbol)

            open_positions = query.all()

            for position in open_positions:
                # 计算未实现盈亏
                # 保证金 = (开仓价 * 数量) / 杠杆，杠杆效果已体现在保证金比例上
                # 盈亏 = 价格变动 * 数量（不再重复乘杠杆，否则等效杠杆²）
                if position.side == TradeSide.LONG:
                    # 做多：(当前价 - 开仓价) * 数量
                    pnl = (current_price - position.entry_price) * position.quantity
                else:
                    # 做空：(开仓价 - 当前价) * 数量
                    pnl = (position.entry_price - current_price) * position.quantity

                position.unrealized_pnl = pnl

            db.commit()
            if open_positions:
                symbol_info = f" ({symbol})" if symbol else ""
                logger.info(f"已更新 {len(open_positions)} 个持仓的盈亏{symbol_info}")
        except Exception as e:
            logger.error(f"更新持仓盈亏失败: {e}")
            db.rollback()

    def check_liquidation(self, db: Session):
        """
        检查并执行爆仓逻辑

        Args:
            db: 数据库会话
        """
        try:
            open_positions = db.query(Position).filter(Position.is_open == True).all()
            liquidated_count = 0

            for position in open_positions:
                # 计算亏损率 = |未实现盈亏| / 保证金
                if position.margin <= 0:
                    continue

                loss_rate = abs(min(position.unrealized_pnl, 0)) / position.margin

                # 亏损率超过阈值，触发爆仓
                if loss_rate >= settings.LIQUIDATION_THRESHOLD:
                    self._execute_liquidation(db, position)
                    liquidated_count += 1

            if liquidated_count > 0:
                db.commit()
                logger.warning(f"执行爆仓 {liquidated_count} 笔")
        except Exception as e:
            logger.error(f"爆仓检查失败: {e}")
            db.rollback()

    def _execute_liquidation(self, db: Session, position: Position):
        """
        执行强制平仓

        Args:
            db: 数据库会话
            position: 持仓对象
        """
        try:
            # 获取用户
            user = db.query(User).filter(User.id == position.user_id).first()
            if not user:
                return

            # 平仓不退还保证金（全部亏损）
            pnl = -position.margin

            # 更新持仓状态
            position.is_open = False
            position.closed_at = get_local_time()

            # 记录交易历史
            trade = Trade(
                user_id=user.id,
                symbol=position.symbol,
                side=TradeSide.SELL if position.side == TradeSide.LONG else TradeSide.BUY,
                price=0,  # 爆仓时价格不记录
                quantity=position.quantity,
                leverage=position.leverage,
                pnl=pnl,
                trade_type=TradeType.LIQUIDATION,
            )
            db.add(trade)

            # 更新用户余额（保证金已被扣除，无需操作）
            user.updated_at = get_local_time()

            logger.warning(
                f"用户 {user.username} 的持仓已爆仓: {position.symbol} "
                f"{position.side.value} 亏损 {pnl:.2f} USDT"
            )
        except Exception as e:
            logger.error(f"执行爆仓失败: {e}")

    async def ai_decision_engine(self, db: Session, current_price: float, user_id: Optional[int] = None) -> Optional[Dict]:
        """
        AI 决策引擎（Claude API 集成）

        Args:
            db: 数据库会话
            current_price: 当前市场价格
            user_id: 用户ID（可选，用于记录决策日志）

        Returns:
            决策信号字典，包含 action, leverage, quantity 等，或 None
        """
        try:
            # 导入AI服务
            from backend.services.ai_service import ai_service

            # 获取激活的提示词配置
            active_prompt = (
                db.query(PromptConfig).filter(PromptConfig.is_active == True).first()
            )

            if not active_prompt:
                logger.debug("无激活的 AI 策略")
                return None

            logger.info(f"使用策略: {active_prompt.name}")

            # 获取历史价格数据
            price_history = self.get_price_history(db, settings.TRADING_PAIR, hours=1)

            # 调用 Claude AI 进行市场分析
            analysis_result = await ai_service.analyze_market(
                symbol=settings.TRADING_PAIR,
                current_price=current_price,
                price_history=price_history,
                prompt_config=active_prompt.prompt_text
            )

            # 构建市场上下文
            market_context = f"当前 {settings.TRADING_PAIR} 价格: ${current_price:.2f}, 波动率: {analysis_result.get('volatility', 'N/A')}"

            # 记录决策日志
            decision_log = AIDecisionLog(
                user_id=user_id,
                prompt_name=active_prompt.name,
                market_context=market_context,
                ai_reasoning=analysis_result["reasoning"],
                decision=analysis_result["decision"],
                action_taken=(analysis_result["decision"] != "HOLD"),
            )
            db.add(decision_log)
            db.commit()

            if analysis_result["decision"] == "HOLD":
                logger.info(f"AI 建议观望: {analysis_result['reasoning']}")
                return None

            decision = {
                "action": analysis_result["decision"],
                "symbol": settings.TRADING_PAIR,
                "price": current_price,
                "leverage": analysis_result["suggested_leverage"],
                "quantity": analysis_result["suggested_quantity"],
                "confidence": analysis_result["confidence"],
                "reasoning": analysis_result["reasoning"]
            }

            logger.info(f"AI 决策: {decision}")
            return decision

        except Exception as e:
            logger.error(f"AI 决策失败: {e}")
            db.rollback()
            return None

    def get_price_history(self, db: Session, symbol: str, hours: int = 1) -> List[Dict]:
        """
        获取历史价格数据

        Args:
            db: 数据库会话
            symbol: 交易对
            hours: 查询最近 N 小时的数据

        Returns:
            价格历史列表
        """
        from datetime import timedelta

        try:
            cutoff_time = get_local_time() - timedelta(hours=hours)
            prices = (
                db.query(MarketPrice)
                .filter(
                    MarketPrice.symbol == symbol, MarketPrice.timestamp >= cutoff_time
                )
                .order_by(MarketPrice.timestamp.asc())
                .all()
            )

            return [
                {
                    "price": p.price,
                    "timestamp": p.timestamp.isoformat(),
                }
                for p in prices
            ]
        except Exception as e:
            logger.error(f"获取价格历史失败: {e}")
            return []


# 全局单例
trading_engine = TradingEngine()
