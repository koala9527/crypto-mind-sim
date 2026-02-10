"""
用户配置管理 API 路由
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from backend.core.database import get_db
from backend.core.models import User, Position, Trade, AIDecisionLog, AIConversation, PromptConfig
from backend.core.config import settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/users", tags=["Users"])


class AIConfigUpdate(BaseModel):
    """AI 配置更新"""
    api_key: str = Field(..., min_length=1, description="API Key")
    base_url: Optional[str] = Field("https://api.hodlai.fun/v1", description="Base URL")


class AIConfigResponse(BaseModel):
    """AI 配置响应"""
    api_key: str
    base_url: str


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
    user.ai_base_url = config.base_url or "https://api.hodlai.fun/v1"

    db.commit()
    db.refresh(user)

    logger.info(f"用户 {user.username} 更新 AI 配置")

    # 返回配置（API Key 返回脱敏版本）
    masked_key = config.api_key[:8] + "..." + config.api_key[-4:] if len(config.api_key) > 12 else "***"

    return AIConfigResponse(
        api_key=masked_key,
        base_url=user.ai_base_url
    )


@router.get("/{user_id}/ai-config")
async def get_ai_config(
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    获取用户的 AI 配置状态

    返回用户是否已配置 API Key（不返回完整密钥）
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    has_config = bool(user.ai_api_key)

    if has_config:
        masked_key = user.ai_api_key[:8] + "..." + user.ai_api_key[-4:] if len(user.ai_api_key) > 12 else "***"
        return {
            "configured": True,
            "api_key": masked_key,
            "base_url": user.ai_base_url or "https://api.hodlai.fun/v1"
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

    # 删除关联数据
    db.query(Position).filter(Position.user_id == user_id).delete()
    db.query(Trade).filter(Trade.user_id == user_id).delete()
    db.query(AIDecisionLog).filter(AIDecisionLog.user_id == user_id).delete()
    db.query(AIConversation).filter(AIConversation.user_id == user_id).delete()
    db.query(PromptConfig).filter(PromptConfig.user_id == user_id).delete()

    # 重置余额
    user.balance = settings.INITIAL_BALANCE
    user.updated_at = datetime.utcnow()

    db.commit()

    logger.info(f"用户数据已重置: {user.username} (ID: {user_id}), 余额恢复为 {settings.INITIAL_BALANCE}")

    return {
        "message": "数据重置成功",
        "balance": settings.INITIAL_BALANCE,
        "reset_at": datetime.utcnow().isoformat()
    }
