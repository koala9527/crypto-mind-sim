"""
用户配置管理 API 路由
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timedelta
from backend.core.database import get_db
from backend.core.models import User, Position, Trade, AIDecisionLog, AIConversation, PromptConfig, AssetHistory, get_local_time
from backend.core.config import settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/users", tags=["Users"])


class AIConfigUpdate(BaseModel):
    """AI 配置更新"""
    api_key: str = Field(..., min_length=1, description="API Key")
    base_url: Optional[str] = Field(None, description="Base URL")
    ai_model: Optional[str] = Field("claude-4.5-opus", description="AI 模型名称")


class AIConfigResponse(BaseModel):
    """AI 配置响应"""
    api_key: str
    base_url: str
    ai_model: str


@router.put("/{user_id}/ai-config", response_model=AIConfigResponse)
async def update_ai_config(
    user_id: int,
    config: AIConfigUpdate,
    db: Session = Depends(get_db)
):
    """
    更新用户的 AI 配置

    将用户在前端配置的 API Key 和 Base URL 同步到服务器，
    以便策略执行器可以自动运行策略
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 更新 AI 配置
    user.ai_api_key = config.api_key
    user.ai_base_url = config.base_url or ""
    user.ai_model = config.ai_model or "claude-4.5-opus"

    db.commit()
    db.refresh(user)

    logger.info(f"用户 {user.username} 更新 AI 配置")

    # 返回完整配置（包含完整 API Key）
    return AIConfigResponse(
        api_key=config.api_key,
        base_url=user.ai_base_url,
        ai_model=user.ai_model or "claude-4.5-opus"
    )


@router.get("/{user_id}/ai-config")
async def get_ai_config(
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    获取用户的 AI 配置状态

    返回用户的完整 API Key（用于前端配置）
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    has_config = bool(user.ai_api_key)

    if has_config:
        return {
            "configured": True,
            "api_key": user.ai_api_key,
            "base_url": user.ai_base_url or "",
            "ai_model": user.ai_model or "claude-4.5-opus"
        }
    else:
        return {
            "configured": False,
            "api_key": None,
            "base_url": None
        }


@router.delete("/{user_id}/ai-config", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ai_config(
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    删除用户的 AI 配置
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    user.ai_api_key = None
    user.ai_base_url = None

    db.commit()

    logger.info(f"用户 {user.username} 删除 AI 配置")

    return None


@router.post("/{user_id}/reset", status_code=status.HTTP_200_OK)
async def reset_user_data(user_id: int, db: Session = Depends(get_db)):
    """
    一键重置用户数据

    清除用户的所有交易数据，余额恢复为初始值：
    - 所有持仓记录
    - 所有交易历史
    - AI决策日志
    - AI对话记录
    - 策略配置
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    try:
        # 使用批量删除，减少数据库往返次数
        db.query(Position).filter(Position.user_id == user_id).delete(synchronize_session=False)
        db.query(Trade).filter(Trade.user_id == user_id).delete(synchronize_session=False)
        db.query(AIDecisionLog).filter(AIDecisionLog.user_id == user_id).delete(synchronize_session=False)
        db.query(AIConversation).filter(AIConversation.user_id == user_id).delete(synchronize_session=False)
        db.query(PromptConfig).filter(PromptConfig.user_id == user_id).delete(synchronize_session=False)
        db.query(AssetHistory).filter(AssetHistory.user_id == user_id).delete(synchronize_session=False)

        # 重置余额
        user.balance = settings.INITIAL_BALANCE
        user.updated_at = get_local_time()

        db.commit()

        logger.info(f"用户数据已重置: {user.username} (ID: {user_id}), 余额恢复为 {settings.INITIAL_BALANCE}")

        return {
            "message": "数据重置成功",
            "balance": settings.INITIAL_BALANCE,
            "reset_at": get_local_time().isoformat()
        }
    except Exception as e:
        db.rollback()
        logger.error(f"重置用户数据失败: {e}")
        raise HTTPException(status_code=500, detail=f"重置失败: {str(e)}")


@router.get("/{user_id}/asset-history")
async def get_asset_history(
    user_id: int,
    hours: int = 24,
    db: Session = Depends(get_db)
):
    """获取用户总资产历史曲线数据"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    since = get_local_time() - timedelta(hours=hours)
    records = (
        db.query(AssetHistory)
        .filter(AssetHistory.user_id == user_id, AssetHistory.timestamp >= since)
        .order_by(AssetHistory.timestamp.asc())
        .all()
    )

    return {
        "data": [
            {
                "timestamp": r.timestamp.isoformat(),
                "total_assets": r.total_assets,
                "balance": r.balance,
                "position_value": r.position_value,
            }
            for r in records
        ],
        "initial_balance": user.initial_balance,
    }
