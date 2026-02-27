"""
FastAPI 主应用 - 路由和定时任务
"""
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
import logging
from apscheduler.schedulers.background import BackgroundScheduler

from backend.core.database import get_db, init_db
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


class TradeResponse(BaseModel):
    id: int
    symbol: str
    side: TradeSide
    price: float
    quantity: float
    leverage: int
    pnl: float
    trade_type: TradeType
    created_at: datetime

    class Config:
        from_attributes = True


class PromptCreate(BaseModel):
    name: str
    description: Optional[str] = None
    prompt_text: str
    ai_model: Optional[str] = "claude-4.5-opus"
    symbol: Optional[str] = "BTC/USDT"


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


def scheduled_price_update():
    """定时任务:更新价格、持仓盈亏、检查爆仓"""
    logger.debug("定时任务:更新价格和持仓")
    from backend.core.database import SessionLocal
    from backend.api.strategy_routes import AVAILABLE_SYMBOLS
    from backend.core.models import MarketPrice

    db = SessionLocal()
    try:
        # 获取并保存所有支持交易对的价格
        for symbol_info in AVAILABLE_SYMBOLS:
            symbol = symbol_info["symbol"]
            try:
                # 获取当前价格
                current_price = trading_engine.fetch_current_price(symbol)
                if current_price is None:
                    logger.warning(f"{symbol} 价格获取失败，跳过")
                    continue

                # 保存价格到数据库
                trading_engine.save_price_to_db(db, symbol, current_price)
                logger.debug(f"保存 {symbol} 价格: ${current_price:.2f}")

            except Exception as e:
                logger.error(f"更新 {symbol} 价格失败: {e}")
                continue

        # 更新所有持仓的盈亏（遍历所有交易对的持仓）
        for symbol_info in AVAILABLE_SYMBOLS:
            symbol = symbol_info["symbol"]
            try:
                # 获取该交易对的最新价格
                latest_price = (
                    db.query(MarketPrice)
                    .filter(MarketPrice.symbol == symbol)
                    .order_by(MarketPrice.timestamp.desc())
                    .first()
                )
                if latest_price:
                    trading_engine.update_positions_pnl(db, latest_price.price, symbol)
            except Exception as e:
                logger.error(f"更新 {symbol} 持仓盈亏失败: {e}")

        # 检查爆仓（所有交易对）
        trading_engine.check_liquidation(db)

        # 记录所有用户的总资产快照
        users = db.query(User).all()
        for user in users:
            open_positions = db.query(Position).filter(
                Position.user_id == user.id,
                Position.is_open == True
            ).all()
            position_value = sum(p.margin + p.unrealized_pnl for p in open_positions)
            total_assets = user.balance + position_value
            snapshot = AssetHistory(
                user_id=user.id,
                total_assets=total_assets,
                balance=user.balance,
                position_value=position_value,
            )
            db.add(snapshot)
        db.commit()

    except Exception as e:
        logger.error(f"定时任务执行失败: {e}")
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
def register_user(user_data: UserRegister, db: Session = Depends(get_db)):
    """注册用户"""
    # 检查用户名是否已存在
    existing_user = db.query(User).filter(User.username == user_data.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="用户名已存在")

    # 创建新用户（实际应使用密码哈希）
    new_user = User(
        username=user_data.username,
        password=user_data.password,  # 简单存储，生产环境应使用 bcrypt 等加密
        balance=settings.INITIAL_BALANCE,
        initial_balance=settings.INITIAL_BALANCE,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    logger.debug(f"新用户注册: {new_user.username}")
    return new_user


@app.post("/api/login", response_model=UserResponse)
def login_user(user_data: UserLogin, db: Session = Depends(get_db)):
    """用户登录"""
    user = db.query(User).filter(User.username == user_data.username).first()
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    # 验证密码（简单比较，生产环境应使用密码哈希验证）
    if user.password != user_data.password:
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    logger.debug(f"用户登录: {user.username}")
    return user


@app.get("/api/users/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)):
    """获取用户信息"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user


@app.delete("/api/users/{user_id}", status_code=status.HTTP_200_OK)
def delete_user(user_id: int, db: Session = Depends(get_db)):
    """
    注销用户账号

    删除用户及其所有相关数据：
    - 用户信息
    - 所有持仓记录
    - 所有交易历史
    - AI决策日志
    - AI对话记录
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    username = user.username

    # 由于在 models.py 中已设置 cascade="all, delete-orphan"
    # 以及 ForeignKey 的 ondelete="CASCADE"
    # 直接删除用户会自动级联删除所有关联数据
    db.delete(user)
    db.commit()

    logger.info(f"用户已注销: {username} (ID: {user_id})")

    return {
        "message": "账号注销成功",
        "username": username,
        "deleted_at": get_local_time().isoformat()
    }



# ---------- 持仓管理 ----------


@app.get("/api/users/{user_id}/positions", response_model=List[PositionResponse])
def get_user_positions(user_id: int, db: Session = Depends(get_db)):
    """获取用户持仓"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    positions = (
        db.query(Position)
        .filter(Position.user_id == user_id, Position.is_open == True)
        .all()
    )
    return positions


@app.post(
    "/api/users/{user_id}/positions",
    response_model=PositionResponse,
    status_code=status.HTTP_201_CREATED,
)
def open_position(
    user_id: int, position_data: PositionCreate, db: Session = Depends(get_db)
):
    """开仓"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 获取当前价格
    current_price = trading_engine.fetch_current_price(position_data.symbol)
    if current_price is None:
        raise HTTPException(status_code=500, detail="无法获取市场价格")

    # 计算保证金 (保证金 = 仓位价值 / 杠杆)
    margin = (current_price * position_data.quantity) / position_data.leverage

    # 检查余额是否足够
    if user.balance < margin:
        raise HTTPException(status_code=400, detail="余额不足")

    # 扣除保证金
    user.balance -= margin
    user.updated_at = get_local_time()

    # 创建持仓
    new_position = Position(
        user_id=user_id,
        symbol=position_data.symbol,
        side=position_data.side,
        entry_price=current_price,
        quantity=position_data.quantity,
        leverage=position_data.leverage,
        margin=margin,
    )
    db.add(new_position)

    # 记录交易历史
    trade = Trade(
        user_id=user_id,
        symbol=position_data.symbol,
        side=TradeSide.BUY if position_data.side == TradeSide.LONG else TradeSide.SELL,
        price=current_price,
        quantity=position_data.quantity,
        leverage=position_data.leverage,
        trade_type=TradeType.OPEN,
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

    # 记录交易历史
    trade = Trade(
        user_id=user.id,
        symbol=position.symbol,
        side=TradeSide.SELL if position.side == TradeSide.LONG else TradeSide.BUY,
        price=current_price,
        quantity=position.quantity,
        leverage=position.leverage,
        pnl=pnl,
        trade_type=TradeType.CLOSE,
    )
    db.add(trade)

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
):
    """获取用户交易历史（分页）"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

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
        "trades": [TradeResponse.model_validate(t) for t in trades],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


@app.get("/api/trades/{trade_id}", response_model=TradeResponse)
def get_trade_detail(trade_id: int, db: Session = Depends(get_db)):
    """获取单个交易详情"""
    trade = db.query(Trade).filter(Trade.id == trade_id).first()
    if not trade:
        raise HTTPException(status_code=404, detail="交易不存在")
    return trade


# ---------- 行情数据 ----------


@app.get("/api/market/overview", response_model=List[MarketOverview])
def get_market_overview():
    """获取首页市场概览（多个币种）"""
    symbols = ["BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "XRP/USDT"]
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
def create_prompt(prompt_data: PromptCreate, db: Session = Depends(get_db)):
    """创建提示词配置"""
    # 检查名称是否已存在
    existing = db.query(PromptConfig).filter(PromptConfig.name == prompt_data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="提示词名称已存在")

    new_prompt = PromptConfig(
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
def get_prompts(db: Session = Depends(get_db)):
    """获取所有提示词"""
    prompts = db.query(PromptConfig).all()
    return prompts


@app.put("/api/prompts/{prompt_id}/activate", response_model=PromptResponse)
def activate_prompt(prompt_id: int, db: Session = Depends(get_db)):
    """激活指定提示词（同时停用其他）"""
    prompt = db.query(PromptConfig).filter(PromptConfig.id == prompt_id).first()
    if not prompt:
        raise HTTPException(status_code=404, detail="提示词不存在")

    # 停用所有提示词
    db.query(PromptConfig).update({"is_active": False})

    # 激活指定提示词
    prompt.is_active = True
    prompt.updated_at = get_local_time()

    db.commit()
    db.refresh(prompt)

    logger.info(f"激活提示词: {prompt.name}")
    return prompt


@app.get("/api/prompts/{prompt_id}", response_model=PromptResponse)
def get_prompt(prompt_id: int, db: Session = Depends(get_db)):
    """获取单个提示词详情"""
    prompt = db.query(PromptConfig).filter(PromptConfig.id == prompt_id).first()
    if not prompt:
        raise HTTPException(status_code=404, detail="提示词不存在")
    return prompt


@app.put("/api/prompts/{prompt_id}", response_model=PromptResponse)
def update_prompt(prompt_id: int, prompt_data: PromptCreate, db: Session = Depends(get_db)):
    """更新提示词配置"""
    prompt = db.query(PromptConfig).filter(PromptConfig.id == prompt_id).first()
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
def reset_prompt_to_default(prompt_id: int, db: Session = Depends(get_db)):
    """重置提示词为默认预设"""
    from backend.utils.init_prompts import DEFAULT_PROMPTS

    prompt = db.query(PromptConfig).filter(PromptConfig.id == prompt_id).first()
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
def get_ai_decisions(user_id: int, limit: int = 50, db: Session = Depends(get_db)):
    """获取用户的 AI 决策日志"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

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
def get_conversations(user_id: int, limit: int = 100, db: Session = Depends(get_db)):
    """获取用户的 AI 对话历史"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

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
    user_id: int, conversation: ConversationCreate, db: Session = Depends(get_db)
):
    """创建用户对话（用户发送消息，Claude AI 回复）"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

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
