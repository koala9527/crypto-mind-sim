"""FastAPI 主应用 - 路由和定时任务。"""

from fastapi import FastAPI, Depends, HTTPException, Response, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, timedelta
import json
import logging
from apscheduler.schedulers.background import BackgroundScheduler

from backend.core.database import get_db, init_db
from backend.core.security import (
    clear_session_cookie,
    get_current_user,
    hash_password,
    needs_password_upgrade,
    require_same_user,
    set_session_cookie,
    verify_password,
)
from backend.core.trade_utils import (
    calculate_fee,
    calculate_holding_seconds,
    calculate_liquidation_price,
    calculate_notional_value,
    calculate_roi_pct,
    get_risk_level,
)
from backend.core.models import (
    User,
    Position,
    Trade,
    PromptConfig,
    TradeSide,
    TradeType,
    AIDecisionLog,
    AIConversation,
    AssetHistory,
    get_local_time,
)
from backend.engine.engine import trading_engine
from backend.core.config import settings
from backend.core.trading_pairs import DEFAULT_SYMBOL, MARKET_OVERVIEW_SYMBOLS

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# 创建 FastAPI 应用
app = FastAPI(
    title="NeoTrade AI",
    description="加密货币交易模拟平台",
    version="2.2.0",
)

# 挂载静态文件
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")

# 引入 AI 路由
from backend.api.ai_routes import router as ai_router
app.include_router(ai_router)

# 引入策略管理路由
from backend.api.strategy_routes import router as strategy_router
app.include_router(strategy_router)

# 引入用户配置路由
from backend.api.user_routes import router as user_router
app.include_router(user_router)

# 引入市场数据路由
from backend.api.market_routes import router as market_router
app.include_router(market_router)


# ==================== Pydantic 模型 ====================


class UserRegister(BaseModel):
    username: str
    password: str
    ai_api_key: str = Field(..., min_length=1)
    ai_base_url: Optional[str] = None
    ai_model: Optional[str] = "claude-4.5-opus"


class UserLogin(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    balance: float
    initial_balance: float
    created_at: datetime

    class Config:
        from_attributes = True


class PositionCreate(BaseModel):
    symbol: str = settings.TRADING_PAIR
    side: TradeSide
    leverage: int = 1
    quantity: float


class PositionResponse(BaseModel):
    id: int
    symbol: str
    side: TradeSide
    entry_price: float
    quantity: float
    leverage: int
    margin: float
    unrealized_pnl: float
    is_open: bool
    created_at: datetime

    class Config:
        from_attributes = True


class PositionSummaryResponse(PositionResponse):
    current_price: float
    liquidation_price: Optional[float] = None
    notional_value: float
    roi_pct: Optional[float] = None
    price_change_pct: Optional[float] = None
    estimated_fee_to_close: float = 0.0
    distance_to_liquidation_pct: Optional[float] = None
    holding_seconds: Optional[int] = None
    risk_level: str = "LOW"


class PositionDetailResponse(PositionSummaryResponse):
    break_even_price: Optional[float] = None
    status_text: str
    position_explanation: str
    next_action_tip: str


class BulkClosePositionsRequest(BaseModel):
    symbols: Optional[List[str]] = None


class BulkClosePositionsResponse(BaseModel):
    closed_count: int
    requested_symbols: List[str]
    total_pnl: float
    total_fee_paid: float


class TradeResponse(BaseModel):
    id: int
    symbol: str
    side: TradeSide
    position_side: Optional[TradeSide] = None
    price: float
    quantity: float
    leverage: int
    margin_used: Optional[float] = None
    notional_value: Optional[float] = None
    pnl: float
    fee_paid: float = 0.0
    balance_before: Optional[float] = None
    balance_after: Optional[float] = None
    roi_pct: Optional[float] = None
    holding_seconds: Optional[int] = None
    entry_price_snapshot: Optional[float] = None
    liquidation_price_snapshot: Optional[float] = None
    close_reason: Optional[str] = None
    execution_source: Optional[str] = None
    market_data: Optional[str] = None
    error_message: Optional[str] = None
    trade_type: TradeType
    created_at: datetime

    class Config:
        from_attributes = True


class PromptCreate(BaseModel):
    name: str
    description: Optional[str] = None
    prompt_text: str
    ai_model: Optional[str] = "claude-4.5-opus"
    symbol: Optional[str] = DEFAULT_SYMBOL


class PromptResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    prompt_text: str
    ai_model: str
    symbol: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class LeaderboardEntry(BaseModel):
    username: str
    total_assets: float
    roi: float
    balance: float


class PriceResponse(BaseModel):
    symbol: str
    price: float
    timestamp: datetime


class StatsResponse(BaseModel):
    total_users: int
    total_positions: int
    total_trades: int
    active_prompts: int


class AIDecisionLogResponse(BaseModel):
    id: int
    prompt_name: str
    market_context: Optional[str]
    ai_reasoning: Optional[str]
    decision: str
    action_taken: bool
    created_at: datetime

    class Config:
        from_attributes = True


class AIConversationResponse(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationCreate(BaseModel):
    content: str


class MarketOverview(BaseModel):
    symbol: str
    price: Optional[float]
    change_24h: Optional[float] = 0.0  # 24小时涨跌幅


# ==================== 定时任务 ====================


def calculate_position_pnl(position: Position, current_price: float) -> float:
    if position.side == TradeSide.LONG:
        return round(
            (current_price - position.entry_price) * position.quantity * position.leverage,
            8,
        )
    return round(
        (position.entry_price - current_price) * position.quantity * position.leverage,
        8,
    )


def calculate_price_change_pct(entry_price: float, current_price: float) -> float | None:
    if not entry_price:
        return None
    return round(((current_price - entry_price) / entry_price) * 100, 4)


def calculate_distance_to_liquidation_pct(
    position: Position, current_price: float
) -> float | None:
    if not position.liquidation_price or not current_price:
        return None

    if position.side == TradeSide.LONG:
        distance = (current_price - position.liquidation_price) / current_price
    else:
        distance = (position.liquidation_price - current_price) / current_price
    return round(distance * 100, 4)


def calculate_break_even_price(position: Position, current_price: float) -> float | None:
    if not position.quantity or not position.leverage:
        return None

    open_fee = calculate_fee(position.entry_price, position.quantity)
    close_fee = calculate_fee(current_price, position.quantity)
    price_delta = (open_fee + close_fee) / (position.quantity * position.leverage)

    if position.side == TradeSide.LONG:
        return round(position.entry_price + price_delta, 8)
    return round(max(position.entry_price - price_delta, 0), 8)


def get_position_status_text(unrealized_pnl: float) -> str:
    if unrealized_pnl > 0.01:
        return "浮盈中"
    if unrealized_pnl < -0.01:
        return "浮亏中"
    return "接近保本"


def get_position_explanation(side: TradeSide) -> str:
    if side == TradeSide.LONG:
        return "做多表示你判断价格会上涨，当前价高于开仓价时通常更容易出现浮盈。"
    return "做空表示你判断价格会下跌，当前价低于开仓价时通常更容易出现浮盈。"


def get_position_next_action_tip(
    status_text: str, risk_level: str, distance_to_liquidation_pct: float | None
) -> str:
    if risk_level == "HIGH" or (
        distance_to_liquidation_pct is not None and distance_to_liquidation_pct <= 3
    ):
        return "当前仓位离爆仓价较近，优先考虑减仓、止损或降低杠杆。"
    if status_text == "浮盈中":
        return "当前处于浮盈阶段，可以结合计划考虑分批止盈或继续观察趋势。"
    if status_text == "浮亏中":
        return "当前处于浮亏阶段，建议先确认是否触发了你的止损规则。"
    return "当前接近盈亏平衡，适合重新检查趋势、成本和风险承受能力。"


def get_position_risk_level(
    leverage: int, distance_to_liquidation_pct: float | None
) -> str:
    base_level = get_risk_level(leverage)
    if distance_to_liquidation_pct is None:
        return base_level
    if distance_to_liquidation_pct <= 3:
        return "HIGH"
    if distance_to_liquidation_pct <= 8 and base_level == "LOW":
        return "MEDIUM"
    return base_level


def build_position_summary(
    position: Position, current_price: float | None = None
) -> PositionSummaryResponse:
    latest_price = current_price
    if latest_price is None:
        latest_price = trading_engine.fetch_current_price(position.symbol)
    if latest_price is None:
        latest_price = position.entry_price

    unrealized_pnl = (
        calculate_position_pnl(position, latest_price)
        if position.is_open
        else position.unrealized_pnl
    )

    notional_value = calculate_notional_value(latest_price, position.quantity)
    roi_pct = calculate_roi_pct(unrealized_pnl, position.margin)
    price_change_pct = calculate_price_change_pct(position.entry_price, latest_price)
    estimated_fee_to_close = calculate_fee(latest_price, position.quantity)
    holding_seconds = calculate_holding_seconds(position.created_at, get_local_time())
    distance_to_liquidation_pct = calculate_distance_to_liquidation_pct(
        position, latest_price
    )
    risk_level = get_position_risk_level(
        position.leverage, distance_to_liquidation_pct
    )

    return PositionSummaryResponse(
        id=position.id,
        symbol=position.symbol,
        side=position.side,
        entry_price=position.entry_price,
        current_price=latest_price,
        quantity=position.quantity,
        leverage=position.leverage,
        margin=position.margin,
        unrealized_pnl=unrealized_pnl,
        liquidation_price=position.liquidation_price,
        notional_value=notional_value,
        roi_pct=roi_pct,
        price_change_pct=price_change_pct,
        estimated_fee_to_close=estimated_fee_to_close,
        distance_to_liquidation_pct=distance_to_liquidation_pct,
        holding_seconds=holding_seconds,
        risk_level=risk_level,
        is_open=position.is_open,
        created_at=position.created_at,
    )


def serialize_trade_response(trade: Trade) -> TradeResponse:
    error_message = None
    if trade.market_data:
        try:
            market_data = json.loads(trade.market_data)
            if isinstance(market_data, dict):
                error_message = market_data.get("error") or market_data.get("exception")
        except json.JSONDecodeError:
            error_message = None

    return TradeResponse(
        id=trade.id,
        symbol=trade.symbol,
        side=trade.side,
        position_side=trade.position_side,
        price=trade.price,
        quantity=trade.quantity,
        leverage=trade.leverage,
        margin_used=trade.margin_used,
        notional_value=trade.notional_value,
        pnl=trade.pnl,
        fee_paid=trade.fee_paid,
        balance_before=trade.balance_before,
        balance_after=trade.balance_after,
        roi_pct=trade.roi_pct,
        holding_seconds=trade.holding_seconds,
        entry_price_snapshot=trade.entry_price_snapshot,
        liquidation_price_snapshot=trade.liquidation_price_snapshot,
        close_reason=trade.close_reason,
        execution_source=trade.execution_source,
        market_data=trade.market_data,
        error_message=error_message,
        trade_type=trade.trade_type,
        created_at=trade.created_at,
    )
    notional_value = calculate_notional_value(latest_price, position.quantity)
    roi_pct = calculate_roi_pct(unrealized_pnl, position.margin)
    price_change_pct = calculate_price_change_pct(position.entry_price, latest_price)
    estimated_fee_to_close = calculate_fee(latest_price, position.quantity)
    holding_seconds = calculate_holding_seconds(position.created_at, get_local_time())
    distance_to_liquidation_pct = calculate_distance_to_liquidation_pct(
        position, latest_price
    )
    risk_level = get_position_risk_level(
        position.leverage, distance_to_liquidation_pct
    )

    return PositionSummaryResponse(
        id=position.id,
        symbol=position.symbol,
        side=position.side,
        entry_price=position.entry_price,
        current_price=latest_price,
        quantity=position.quantity,
        leverage=position.leverage,
        margin=position.margin,
        unrealized_pnl=unrealized_pnl,
        liquidation_price=position.liquidation_price,
        notional_value=notional_value,
        roi_pct=roi_pct,
        price_change_pct=price_change_pct,
        estimated_fee_to_close=estimated_fee_to_close,
        distance_to_liquidation_pct=distance_to_liquidation_pct,
        holding_seconds=holding_seconds,
        risk_level=risk_level,
        is_open=position.is_open,
        created_at=position.created_at,
    )


def scheduled_price_update():
    """定时任务:更新价格、持仓盈亏、检查爆仓"""
    logger.debug("定时任务:更新价格和持仓")
    from backend.core.database import SessionLocal
    from backend.api.strategy_routes import AVAILABLE_SYMBOLS
    from backend.core.models import MarketPrice

    # 第一步：获取并保存所有交易对的价格（快速操作）
    db = SessionLocal()
    try:
        for symbol_info in AVAILABLE_SYMBOLS:
            symbol = symbol_info["symbol"]
            try:
                current_price = trading_engine.fetch_current_price(symbol)
                if current_price is None:
                    logger.warning(f"{symbol} 价格获取失败，跳过")
                    continue

                trading_engine.save_price_to_db(db, symbol, current_price)
                logger.debug(f"保存 {symbol} 价格: ${current_price:.2f}")

            except Exception as e:
                logger.error(f"更新 {symbol} 价格失败: {e}")
                continue
        db.commit()
    except Exception as e:
        logger.error(f"价格更新失败: {e}")
        db.rollback()
    finally:
        db.close()

    # 第二步：更新所有持仓的盈亏（为每个交易对创建独立会话）
    for symbol_info in AVAILABLE_SYMBOLS:
        symbol = symbol_info["symbol"]
        db = SessionLocal()
        try:
            latest_price = (
                db.query(MarketPrice)
                .filter(MarketPrice.symbol == symbol)
                .order_by(MarketPrice.timestamp.desc())
                .first()
            )
            if latest_price:
                trading_engine.update_positions_pnl(db, latest_price.price, symbol)
                db.commit()
        except Exception as e:
            logger.error(f"更新 {symbol} 持仓盈亏失败: {e}")
            db.rollback()
        finally:
            db.close()

    # 第三步：检查爆仓
    db = SessionLocal()
    try:
        trading_engine.check_liquidation(db)
        db.commit()
    except Exception as e:
        logger.error(f"检查爆仓失败: {e}")
        db.rollback()
    finally:
        db.close()

    # 第四步：记录所有用户的总资产快照（批量操作）
    db = SessionLocal()
    try:
        users = db.query(User).all()
        snapshots = []

        for user in users:
            open_positions = db.query(Position).filter(
                Position.user_id == user.id,
                Position.is_open == True
            ).all()
            position_value = sum(p.margin + p.unrealized_pnl for p in open_positions)
            total_assets = user.balance + position_value

            snapshots.append(AssetHistory(
                user_id=user.id,
                total_assets=total_assets,
                balance=user.balance,
                position_value=position_value,
            ))

        # 批量插入
        if snapshots:
            db.bulk_save_objects(snapshots)
        db.commit()
    except Exception as e:
        logger.error(f"记录资产快照失败: {e}")
        db.rollback()
    finally:
        db.close()


def scheduled_strategy_execution():
    """定时任务：执行激活的策略"""
    import asyncio
    from backend.engine.strategy_executor import execute_active_strategies

    logger.debug("执行定时任务：策略执行")
    try:
        # 在新的事件循环中运行异步任务
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(execute_active_strategies())
        loop.close()
    except Exception as e:
        logger.error(f"策略执行任务失败: {e}")


# ==================== 事件处理 ====================


@app.on_event("startup")
def startup_event():
    """应用启动时执行"""
    logger.info("NeoTrade AI 启动中...")

    # 初始化数据库
    init_db()
    logger.info("数据库初始化完成")

    if settings.DISABLE_SCHEDULER:
        logger.info("已禁用定时任务调度器")
        return

    # 启动定时任务
    scheduler = BackgroundScheduler()

    # 价格更新任务
    scheduler.add_job(
        scheduled_price_update,
        "interval",
        seconds=settings.PRICE_UPDATE_INTERVAL,
        id="price_update",
    )
    logger.info(f"价格更新任务已启动，间隔 {settings.PRICE_UPDATE_INTERVAL} 秒")

    # 策略执行任务（每分钟执行一次）
    scheduler.add_job(
        scheduled_strategy_execution,
        "interval",
        seconds=60,
        id="strategy_execution",
    )
    logger.info("策略执行任务已启动，间隔 60 秒")

    scheduler.start()

    # 存储调度器到应用状态
    app.state.scheduler = scheduler


@app.on_event("shutdown")
def shutdown_event():
    """应用关闭时执行"""
    if hasattr(app.state, "scheduler"):
        app.state.scheduler.shutdown()
        logger.info("定时任务已停止")


# ==================== 路由 ====================


@app.get("/")
def read_root():
    """返回前端页面"""
    return FileResponse("frontend/static/index.html")


# ---------- 用户管理 ----------


@app.post("/api/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(
    user_data: UserRegister,
    response: Response,
    db: Session = Depends(get_db),
):
    """注册用户"""
    # 检查用户名是否已存在
    existing_user = db.query(User).filter(User.username == user_data.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="用户名已存在")

    # 创建新用户（实际应使用密码哈希）
    new_user = User(
        username=user_data.username,
        password=hash_password(user_data.password),
        balance=settings.INITIAL_BALANCE,
        initial_balance=settings.INITIAL_BALANCE,
        ai_api_key=user_data.ai_api_key,
        ai_base_url=user_data.ai_base_url or "",
        ai_model=user_data.ai_model or "claude-4.5-opus",
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    logger.debug(f"新用户注册: {new_user.username}")
    set_session_cookie(response, new_user.id)
    return new_user


@app.post("/api/login", response_model=UserResponse)
def login_user(
    user_data: UserLogin,
    response: Response,
    db: Session = Depends(get_db),
):
    """用户登录"""
    user = db.query(User).filter(User.username == user_data.username).first()
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    if not verify_password(user_data.password, user.password):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    if needs_password_upgrade(user.password):
        user.password = hash_password(user_data.password)
        db.commit()
        db.refresh(user)

    logger.debug(f"用户登录: {user.username}")
    set_session_cookie(response, user.id)
    return user


@app.post("/api/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout_user(response: Response):
    """退出登录并清理会话 Cookie。"""
    clear_session_cookie(response)
    return None


@app.get("/api/users/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_same_user),
):
    """获取用户信息"""
    if not current_user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return current_user


@app.delete("/api/users/{user_id}", status_code=status.HTTP_200_OK)
def delete_user(
    user_id: int,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_same_user),
):
    """
    注销用户账号

    删除用户及其所有相关数据：
    - 用户信息
    - 所有持仓记录
    - 所有交易历史
    - AI决策日志
    - AI对话记录
    """
    username = current_user.username

    # 由于在 models.py 中已设置 cascade="all, delete-orphan"
    # 以及 ForeignKey 的 ondelete="CASCADE"
    # 直接删除用户会自动级联删除所有关联数据
    db.delete(current_user)
    db.commit()
    clear_session_cookie(response)

    logger.info(f"用户已注销: {username} (ID: {user_id})")

    return {
        "message": "账号注销成功",
        "username": username,
        "deleted_at": get_local_time().isoformat()
    }



# ---------- 持仓管理 ----------


@app.get("/api/users/{user_id}/positions", response_model=List[PositionSummaryResponse])
def get_user_positions(
    user_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_same_user),
):
    """获取用户持仓"""
    positions = (
        db.query(Position)
        .filter(Position.user_id == user_id, Position.is_open == True)
        .all()
    )
    price_cache: dict[str, float] = {}
    summaries = []
    for position in positions:
        if position.symbol not in price_cache:
            latest_price = trading_engine.fetch_current_price(position.symbol)
            price_cache[position.symbol] = latest_price or position.entry_price
        summaries.append(build_position_summary(position, price_cache[position.symbol]))
    return summaries


@app.get("/api/positions/{position_id}", response_model=PositionDetailResponse)
def get_position_detail(
    position_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取单个持仓详情"""
    position = db.query(Position).filter(Position.id == position_id).first()
    if not position:
        raise HTTPException(status_code=404, detail="持仓不存在")
    if position.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权查看该持仓")

    summary = build_position_summary(position)
    status_text = get_position_status_text(summary.unrealized_pnl)

    return PositionDetailResponse(
        **summary.model_dump(),
        break_even_price=calculate_break_even_price(position, summary.current_price),
        status_text=status_text,
        position_explanation=get_position_explanation(position.side),
        next_action_tip=get_position_next_action_tip(
            status_text, summary.risk_level, summary.distance_to_liquidation_pct
        ),
    )


@app.post(
    "/api/users/{user_id}/positions",
    response_model=PositionResponse,
    status_code=status.HTTP_201_CREATED,
)
def open_position(
    user_id: int,
    position_data: PositionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_same_user),
):
    """开仓"""
    user = current_user

    # 获取当前价格
    current_price = trading_engine.fetch_current_price(position_data.symbol)
    if current_price is None:
        raise HTTPException(status_code=500, detail="无法获取市场价格")

    # 计算保证金 (保证金 = 仓位价值 / 杠杆)
    notional_value = calculate_notional_value(current_price, position_data.quantity)
    fee_paid = calculate_fee(current_price, position_data.quantity)
    margin = notional_value / position_data.leverage
    total_cost = margin + fee_paid

    # 检查余额是否足够
    if user.balance < total_cost:
        raise HTTPException(status_code=400, detail="余额不足")

    # 扣除保证金
    balance_before = user.balance
    user.balance -= total_cost
    user.updated_at = get_local_time()
    liquidation_price = calculate_liquidation_price(
        current_price, position_data.leverage, position_data.side
    )

    # 创建持仓
    new_position = Position(
        user_id=user_id,
        symbol=position_data.symbol,
        side=position_data.side,
        entry_price=current_price,
        quantity=position_data.quantity,
        leverage=position_data.leverage,
        margin=margin,
        liquidation_price=liquidation_price,
    )
    db.add(new_position)
    db.flush()

    # 记录交易历史
    trade = Trade(
        user_id=user_id,
        position_id=new_position.id,
        symbol=position_data.symbol,
        side=TradeSide.BUY if position_data.side == TradeSide.LONG else TradeSide.SELL,
        position_side=position_data.side,
        price=current_price,
        quantity=position_data.quantity,
        leverage=position_data.leverage,
        margin_used=margin,
        notional_value=notional_value,
        fee_paid=fee_paid,
        balance_before=balance_before,
        balance_after=user.balance,
        roi_pct=calculate_roi_pct(0.0, margin),
        entry_price_snapshot=current_price,
        liquidation_price_snapshot=liquidation_price,
        close_reason="USER_OPEN",
        execution_source="MANUAL",
        trade_type=TradeType.OPEN,
        market_data=(
            '{'
            f'"risk_level":"{get_risk_level(position_data.leverage)}",'
            f'"fee_rate":{settings.TRADING_FEE_RATE},'
            f'"estimated_total_cost":{round(total_cost, 8)}'
            '}'
        ),
    )
    db.add(trade)

    db.commit()
    db.refresh(new_position)

    logger.info(
        f"用户 {user.username} 开仓: {position_data.symbol} "
        f"{position_data.side.value} {position_data.leverage}x"
    )
    return new_position


@app.delete("/api/positions/{position_id}", status_code=status.HTTP_204_NO_CONTENT)
def close_position(position_id: int, db: Session = Depends(get_db)):
    """平仓"""
    position = db.query(Position).filter(Position.id == position_id).first()
    if not position:
        raise HTTPException(status_code=404, detail="持仓不存在")

    if not position.is_open:
        raise HTTPException(status_code=400, detail="持仓已关闭")

    # 获取用户
    user = db.query(User).filter(User.id == position.user_id).first()

    # 获取当前价格
    current_price = trading_engine.fetch_current_price(position.symbol)
    if current_price is None:
        raise HTTPException(status_code=500, detail="无法获取市场价格")

    # 计算盈亏
    if position.side == TradeSide.LONG:
        pnl = (current_price - position.entry_price) * position.quantity
    else:
        pnl = (position.entry_price - current_price) * position.quantity

    notional_value = calculate_notional_value(current_price, position.quantity)
    fee_paid = calculate_fee(current_price, position.quantity)
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
        close_reason=close_reason,
        execution_source=execution_source,
        trade_type=TradeType.CLOSE,
        market_data=(
            '{'
            f'"exit_price":{round(current_price, 8)},'
            f'"fee_rate":{settings.TRADING_FEE_RATE},'
            f'"close_reason":"{close_reason}"'
            '}'
        ),
    )
    db.add(trade)
    return pnl, fee_paid


@app.post(
    "/api/users/{user_id}/positions/close-all",
    response_model=BulkClosePositionsResponse,
)
def close_positions_by_symbols(
    user_id: int,
    request: BulkClosePositionsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_same_user),
):
    """批量平仓，支持按交易对筛选。"""
    positions_query = db.query(Position).filter(
        Position.user_id == current_user.id,
        Position.is_open == True,
    )

    requested_symbols = [symbol for symbol in (request.symbols or []) if symbol]
    if requested_symbols:
        positions_query = positions_query.filter(Position.symbol.in_(requested_symbols))

    positions = positions_query.all()
    if not positions:
        return BulkClosePositionsResponse(
            closed_count=0,
            requested_symbols=requested_symbols,
            total_pnl=0.0,
            total_fee_paid=0.0,
        )

    price_cache: dict[str, float] = {}
    total_pnl = 0.0
    total_fee_paid = 0.0

    for position in positions:
        if position.symbol not in price_cache:
            latest_price = trading_engine.fetch_current_price(position.symbol)
            if latest_price is None:
                raise HTTPException(status_code=500, detail=f"无法获取 {position.symbol} 市场价格")
            price_cache[position.symbol] = latest_price

        pnl, fee_paid = close_position_record(
            db,
            current_user,
            position,
            price_cache[position.symbol],
            close_reason="SYMBOL_SWITCH_CLOSE",
            execution_source="MANUAL_BULK_CLOSE",
        )
        total_pnl += pnl
        total_fee_paid += fee_paid

    db.commit()

    logger.info(
        f"用户 {current_user.username} 批量平仓 {len(positions)} 笔持仓，symbols={requested_symbols or 'ALL'}"
    )

    return BulkClosePositionsResponse(
        closed_count=len(positions),
        requested_symbols=requested_symbols,
        total_pnl=round(total_pnl, 8),
        total_fee_paid=round(total_fee_paid, 8),
    )


@app.delete("/api/positions/{position_id}", status_code=status.HTTP_204_NO_CONTENT)
def close_position(
    position_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """平仓"""
    position = db.query(Position).filter(Position.id == position_id).first()
    if not position:
        raise HTTPException(status_code=404, detail="持仓不存在")

    if position.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权操作该持仓")

    if not position.is_open:
        raise HTTPException(status_code=400, detail="持仓已关闭")

    user = current_user
    current_price = trading_engine.fetch_current_price(position.symbol)
    if current_price is None:
        raise HTTPException(status_code=500, detail="无法获取市场价格")
    pnl, _fee_paid = close_position_record(db, user, position, current_price)

    db.commit()

    logger.info(
        f"用户 {user.username} 平仓: {position.symbol} "
        f"{position.side.value} 盈亏 {pnl:.2f} USDT"
    )
    return None


# ---------- 交易历史 ----------


@app.get("/api/users/{user_id}/trades")
def get_user_trades(
    user_id: int,
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_same_user),
):
    """获取用户交易历史（分页）"""
    if page < 1:
        page = 1
    if page_size < 1 or page_size > 100:
        page_size = 10

    total = db.query(Trade).filter(Trade.user_id == user_id).count()
    total_pages = max(1, (total + page_size - 1) // page_size)

    trades = (
        db.query(Trade)
        .filter(Trade.user_id == user_id)
        .order_by(Trade.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "trades": [serialize_trade_response(t) for t in trades],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


@app.get("/api/trades/{trade_id}", response_model=TradeResponse)
def get_trade_detail(
    trade_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取单个交易详情"""
    trade = db.query(Trade).filter(Trade.id == trade_id).first()
    if not trade:
        raise HTTPException(status_code=404, detail="交易不存在")
    if trade.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权查看该交易")
    return serialize_trade_response(trade)


# ---------- 行情数据 ----------


@app.get("/api/market/overview", response_model=List[MarketOverview])
def get_market_overview():
    """获取首页市场概览（多个币种）"""
    symbols = MARKET_OVERVIEW_SYMBOLS
    prices = trading_engine.fetch_multiple_prices(symbols)

    overview = []
    for symbol in symbols:
        overview.append(
            MarketOverview(
                symbol=symbol,
                price=prices.get(symbol),
                change_24h=0.0,  # 简化版，暂不计算24h涨跌
            )
        )

    return overview


@app.get("/api/price/current", response_model=PriceResponse)
def get_current_price(db: Session = Depends(get_db)):
    """获取当前价格"""
    from backend.core.models import MarketPrice

    latest_price = (
        db.query(MarketPrice)
        .filter(MarketPrice.symbol == settings.TRADING_PAIR)
        .order_by(MarketPrice.timestamp.desc())
        .first()
    )

    if not latest_price:
        # 如果数据库中没有价格，实时获取
        current_price = trading_engine.fetch_current_price()
        if current_price is None:
            raise HTTPException(status_code=500, detail="无法获取市场价格")

        return PriceResponse(
            symbol=settings.TRADING_PAIR,
            price=current_price,
            timestamp=get_local_time(),
        )

    return PriceResponse(
        symbol=latest_price.symbol,
        price=latest_price.price,
        timestamp=latest_price.timestamp,
    )


@app.get("/api/price/history")
def get_price_history(hours: int = 1, symbol: str = None, db: Session = Depends(get_db)):
    """获取历史价格"""
    target_symbol = symbol or settings.TRADING_PAIR
    history = trading_engine.get_price_history(db, target_symbol, hours)
    return {"symbol": target_symbol, "data": history}


# ---------- 排行榜 ----------


@app.get("/api/leaderboard", response_model=List[LeaderboardEntry])
def get_leaderboard(db: Session = Depends(get_db)):
    """获取排行榜（Top 10）"""
    users = db.query(User).all()
    leaderboard = []

    for user in users:
        # 计算总资产 = 余额 + 所有持仓的(保证金 + 未实现盈亏)
        positions = (
            db.query(Position)
            .filter(Position.user_id == user.id, Position.is_open == True)
            .all()
        )

        total_position_value = sum(p.margin + p.unrealized_pnl for p in positions)
        total_assets = user.balance + total_position_value

        # 计算 ROI
        roi = ((total_assets - user.initial_balance) / user.initial_balance) * 100

        leaderboard.append(
            LeaderboardEntry(
                username=user.username,
                total_assets=total_assets,
                roi=roi,
                balance=user.balance,
            )
        )

    # 按总资产降序排序
    leaderboard.sort(key=lambda x: x.total_assets, reverse=True)

    return leaderboard[: settings.LEADERBOARD_TOP_N]


# ---------- AI 策略 ----------


@app.post(
    "/api/prompts", response_model=PromptResponse, status_code=status.HTTP_201_CREATED
)
def create_prompt(
    prompt_data: PromptCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建提示词配置"""
    # 检查名称是否已存在
    existing = db.query(PromptConfig).filter(
        PromptConfig.user_id == current_user.id,
        PromptConfig.name == prompt_data.name,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="提示词名称已存在")

    new_prompt = PromptConfig(
        user_id=current_user.id,
        name=prompt_data.name,
        description=prompt_data.description,
        prompt_text=prompt_data.prompt_text,
        ai_model=prompt_data.ai_model,
        symbol=prompt_data.symbol,
    )
    db.add(new_prompt)
    db.commit()
    db.refresh(new_prompt)

    logger.info(f"创建提示词: {new_prompt.name}")
    return new_prompt


@app.get("/api/prompts", response_model=List[PromptResponse])
def get_prompts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取所有提示词"""
    prompts = db.query(PromptConfig).filter(
        PromptConfig.user_id == current_user.id
    ).all()
    return prompts


@app.put("/api/prompts/{prompt_id}/activate", response_model=PromptResponse)
def activate_prompt(
    prompt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """激活指定提示词（同时停用其他）"""
    prompt = db.query(PromptConfig).filter(
        PromptConfig.id == prompt_id,
        PromptConfig.user_id == current_user.id,
    ).first()
    if not prompt:
        raise HTTPException(status_code=404, detail="提示词不存在")

    # 停用所有提示词
    db.query(PromptConfig).filter(
        PromptConfig.user_id == current_user.id
    ).update({"is_active": False})

    # 激活指定提示词
    prompt.is_active = True
    prompt.updated_at = get_local_time()

    db.commit()
    db.refresh(prompt)

    logger.info(f"激活提示词: {prompt.name}")
    return prompt


@app.get("/api/prompts/{prompt_id}", response_model=PromptResponse)
def get_prompt(
    prompt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取单个提示词详情"""
    prompt = db.query(PromptConfig).filter(
        PromptConfig.id == prompt_id,
        PromptConfig.user_id == current_user.id,
    ).first()
    if not prompt:
        raise HTTPException(status_code=404, detail="提示词不存在")
    return prompt


@app.put("/api/prompts/{prompt_id}", response_model=PromptResponse)
def update_prompt(
    prompt_id: int,
    prompt_data: PromptCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新提示词配置"""
    prompt = db.query(PromptConfig).filter(
        PromptConfig.id == prompt_id,
        PromptConfig.user_id == current_user.id,
    ).first()
    if not prompt:
        raise HTTPException(status_code=404, detail="提示词不存在")

    # 更新字段
    prompt.name = prompt_data.name
    prompt.description = prompt_data.description
    prompt.prompt_text = prompt_data.prompt_text
    prompt.ai_model = prompt_data.ai_model
    prompt.symbol = prompt_data.symbol
    prompt.updated_at = get_local_time()

    db.commit()
    db.refresh(prompt)

    logger.info(f"更新提示词: {prompt.name}")
    return prompt


@app.get("/api/models")
async def get_available_models():
    """获取可用的 AI 模型列表"""
    from backend.services.ai_service import ai_service
    models = await ai_service.list_models()
    return {"models": models}


@app.post("/api/prompts/{prompt_id}/reset")
def reset_prompt_to_default(
    prompt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """重置提示词为默认预设"""
    from backend.utils.init_prompts import DEFAULT_PROMPTS

    prompt = db.query(PromptConfig).filter(
        PromptConfig.id == prompt_id,
        PromptConfig.user_id == current_user.id,
    ).first()
    if not prompt:
        raise HTTPException(status_code=404, detail="提示词不存在")

    # 查找对应的默认提示词
    default = None
    for preset in DEFAULT_PROMPTS:
        if preset["name"] == prompt.name:
            default = preset
            break

    if not default:
        raise HTTPException(status_code=400, detail="该策略没有默认预设")

    # 重置为默认值
    prompt.description = default.get("description")
    prompt.prompt_text = default["prompt_text"]
    prompt.updated_at = get_local_time()

    db.commit()
    db.refresh(prompt)

    logger.info(f"重置提示词为默认: {prompt.name}")
    return {"message": "已重置为默认预设", "prompt": prompt}


# ---------- 系统统计 ----------


@app.get("/api/stats", response_model=StatsResponse)
def get_stats(db: Session = Depends(get_db)):
    """获取系统统计信息"""
    total_users = db.query(User).count()
    total_positions = db.query(Position).filter(Position.is_open == True).count()
    total_trades = db.query(Trade).count()
    active_prompts = db.query(PromptConfig).filter(PromptConfig.is_active == True).count()

    return StatsResponse(
        total_users=total_users,
        total_positions=total_positions,
        total_trades=total_trades,
        active_prompts=active_prompts,
    )


# ---------- AI 决策日志 ----------


@app.get("/api/users/{user_id}/ai-decisions", response_model=List[AIDecisionLogResponse])
def get_ai_decisions(
    user_id: int,
    limit: int = 50,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_same_user),
):
    """获取用户的 AI 决策日志"""
    decisions = (
        db.query(AIDecisionLog)
        .filter(AIDecisionLog.user_id == user_id)
        .order_by(AIDecisionLog.created_at.desc())
        .limit(limit)
        .all()
    )
    return decisions


# ---------- AI 对话历史 ----------


@app.get("/api/users/{user_id}/conversations", response_model=List[AIConversationResponse])
def get_conversations(
    user_id: int,
    limit: int = 100,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_same_user),
):
    """获取用户的 AI 对话历史"""
    conversations = (
        db.query(AIConversation)
        .filter(AIConversation.user_id == user_id)
        .order_by(AIConversation.created_at.asc())
        .limit(limit)
        .all()
    )
    return conversations


@app.post(
    "/api/users/{user_id}/conversations",
    response_model=AIConversationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_conversation(
    user_id: int,
    conversation: ConversationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_same_user),
):
    """创建用户对话（用户发送消息，Claude AI 回复）"""
    user = current_user

    # 保存用户消息
    user_message = AIConversation(
        user_id=user_id, role="user", content=conversation.content
    )
    db.add(user_message)
    db.flush()  # 确保消息被保存

    try:
        # 导入AI服务
        from backend.services.ai_service import ai_service

        # 获取对话历史
        conversation_history = (
            db.query(AIConversation)
            .filter(AIConversation.user_id == user_id)
            .order_by(AIConversation.created_at.asc())
            .all()
        )

        # 构建对话上下文
        history = [
            {"role": msg.role, "content": msg.content}
            for msg in conversation_history[-10:]  # 最近10条
        ]

        # 获取用户上下文
        positions = db.query(Position).filter(
            Position.user_id == user_id,
            Position.is_open == True
        ).all()

        position_value = sum(p.margin + p.unrealized_pnl for p in positions)
        total_assets = user.balance + position_value

        user_context = {
            "balance": user.balance,
            "position_count": len(positions),
            "total_assets": total_assets
        }

        # 调用 Claude AI
        ai_reply = await ai_service.chat(
            user_message=conversation.content,
            conversation_history=history[:-1],  # 不包含当前消息
            user_context=user_context
        )

        # 保存 AI 回复
        ai_message = AIConversation(user_id=user_id, role="assistant", content=ai_reply)
        db.add(ai_message)
        db.commit()
        db.refresh(ai_message)

        return ai_message

    except Exception as e:
        logger.error(f"AI 对话失败: {e}")
        db.rollback()
        # 返回错误提示
        ai_message = AIConversation(
            user_id=user_id,
            role="assistant",
            content=f"抱歉，AI 服务暂时不可用。错误: {str(e)}"
        )
        db.add(ai_message)
        db.commit()
        db.refresh(ai_message)
        return ai_message
