"""
AI 驱动的自动交易调度器
支持多用户、多策略的智能交易
"""
import asyncio
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from backend.core.database import SessionLocal
from backend.core.models import User, PromptConfig, Position
from backend.engine.engine import TradingEngine
from backend.core.config import settings
from typing import List

logger = logging.getLogger(__name__)


class AITradingScheduler:
    """AI 自动交易调度器"""

    def __init__(self):
        self.trading_engine = TradingEngine()

    async def run_ai_trading_for_all_users(self):
        """为所有启用AI交易的用户执行AI决策"""
        db = SessionLocal()
        try:
            # 获取当前价格
            current_price = self.trading_engine.fetch_current_price()
            if not current_price:
                logger.warning("价格获取失败，跳过AI交易")
                return

            # 获取所有用户
            users = db.query(User).all()

            for user in users:
                try:
                    await self.execute_ai_trading_for_user(db, user, current_price)
                except Exception as e:
                    logger.error(f"用户 {user.username} AI交易失败: {e}")
                    continue

        except Exception as e:
            logger.error(f"AI交易调度失败: {e}")
        finally:
            db.close()

    async def execute_ai_trading_for_user(self, db: Session, user: User, current_price: float):
        """为单个用户执行AI交易决策"""

        # 检查用户是否有足够余额
        if user.balance < 100:  # 最低余额要求
            logger.debug(f"用户 {user.username} 余额不足，跳过AI交易")
            return

        # 检查用户当前持仓数量
        open_positions_count = db.query(Position).filter(
            Position.user_id == user.id,
            Position.is_open == True
        ).count()

        # 限制最大持仓数量
        max_positions = 3
        if open_positions_count >= max_positions:
            logger.debug(f"用户 {user.username} 持仓已达上限，跳过AI交易")
            return

        # 调用AI决策引擎
        decision = await self.trading_engine.ai_decision_engine(
            db=db,
            current_price=current_price,
            user_id=user.id
        )

        if not decision:
            return

        # 验证决策信心度
        confidence_threshold = 0.6  # 信心度阈值
        if decision.get("confidence", 0) < confidence_threshold:
            logger.info(
                f"用户 {user.username} AI决策信心度不足 "
                f"({decision.get('confidence', 0):.2f} < {confidence_threshold})，不执行交易"
            )
            return

        # 执行交易
        try:
            action = decision["action"]
            leverage = decision["leverage"]
            quantity = decision["quantity"]

            # 计算所需保证金
            margin_required = (current_price * quantity * leverage) / leverage

            if user.balance < margin_required:
                logger.warning(
                    f"用户 {user.username} 余额不足，无法执行AI交易 "
                    f"(需要 {margin_required:.2f}, 当前 {user.balance:.2f})"
                )
                return

            # 创建持仓
            position = Position(
                user_id=user.id,
                symbol=settings.TRADING_PAIR,
                side=action,  # "BUY" or "SELL"
                leverage=leverage,
                quantity=quantity,
                entry_price=current_price,
                margin=margin_required,
                unrealized_pnl=0.0,
            )
            db.add(position)

            # 扣除保证金
            user.balance -= margin_required
            user.updated_at = datetime.utcnow()

            db.commit()
            db.refresh(position)

            logger.info(
                f"AI自动交易成功 - 用户: {user.username}, "
                f"动作: {action}, 杠杆: {leverage}x, 数量: {quantity}, "
                f"信心度: {decision.get('confidence', 0):.2f}"
            )

        except Exception as e:
            logger.error(f"执行AI交易失败: {e}")
            db.rollback()


# 全局调度器实例
ai_scheduler = AITradingScheduler()


async def scheduled_ai_trading():
    """定时执行AI交易（异步版本）"""
    logger.info("开始执行AI自动交易...")
    try:
        await ai_scheduler.run_ai_trading_for_all_users()
        logger.info("AI自动交易执行完成")
    except Exception as e:
        logger.error(f"AI自动交易调度失败: {e}")
