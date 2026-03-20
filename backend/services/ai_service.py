"""
AI 服务模块 - 集成多个主流大模型
"""
import httpx
import json
import logging
from typing import List, Dict, Optional
from backend.core.config import settings

logger = logging.getLogger(__name__)


class AIAPIError(Exception):
    """AI API 调用错误，携带 HTTP 状态码和完整响应体"""

    def __init__(self, message: str, status_code: int = 0, response_body: str = ""):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body

# 支持的模型列表（只保留你提供的8个模型）
AVAILABLE_MODELS = {
    "gpt-5.2": {
        "name": "GPT-5.2",
        "provider": "OpenAI",
        "description": "🔥 Flagship",
        "icon": "●"
    },
    "o3-pro": {
        "name": "o3 Pro",
        "provider": "OpenAI",
        "description": "🧠 Reasoning",
        "icon": "●"
    },
    "claude-4.5-opus": {
        "name": "Claude 4.5 Opus",
        "provider": "Anthropic",
        "description": "⭐ Best Value",
        "icon": "A"
    },
    "gemini-3-pro": {
        "name": "Gemini 3 Pro",
        "provider": "Google",
        "description": "🔥 Next Gen",
        "icon": "G"
    },
    "deepseek-r1": {
        "name": "DeepSeek R1",
        "provider": "DeepSeek",
        "description": "🧠 Top Logic",
        "icon": "D"
    },
    "grok-4": {
        "name": "Grok 4",
        "provider": "xAI",
        "description": "🔥 Uncensored",
        "icon": "𝕏"
    },
    "kimi-k2": {
        "name": "Kimi K2",
        "provider": "Moonshot",
        "description": "🔥 MoE Arch",
        "icon": "K"
    },
    "qwen3-max": {
        "name": "Qwen3 Max",
        "provider": "Alibaba",
        "description": "Only文档",
        "icon": "Q"
    }
}


class AIService:
    """AI 服务类 - API Key 和 Base URL 由前端传入"""

    def __init__(self):
        # 默认配置
        self.default_model = "claude-4.5-opus"
        self.temperature = 0.7
        self.max_tokens = 2000

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        api_key: str,
        base_url: str = "",
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Dict:
        """
        调用 Chat Completions API

        Args:
            messages: 对话消息列表
            api_key: API 密钥（必需，由前端传入）
            base_url: API 基础 URL（由前端传入）
            model: 使用的模型，默认使用配置的默认模型
            temperature: 生成温度
            max_tokens: 最大token数

        Returns:
            AI 响应结果
        """
        if not api_key:
            raise ValueError("未配置 API Key，请先在设置中配置")

        model = model or self.default_model
        temperature = temperature or self.temperature
        max_tokens = max_tokens or self.max_tokens

        url = f"{base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                body = response.text.strip()
                if not body:
                    raise ValueError(f"AI API 返回空响应 (status={response.status_code})")
                try:
                    return response.json()
                except Exception:
                    raise ValueError(f"AI API 返回非 JSON 内容 (status={response.status_code}): {body[:200]}")
        except httpx.HTTPStatusError as e:
            body = e.response.text[:2000] if e.response else ""
            status = e.response.status_code if e.response else 0
            # 尝试从响应体中提取 API 提供商的错误描述
            try:
                body_json = json.loads(body)
                api_msg = (
                    (body_json.get("error") or {}).get("message")
                    or body_json.get("message")
                    or body[:300]
                )
            except Exception:
                api_msg = body[:300]
            friendly = f"API HTTP {status}: {api_msg}"
            logger.error(
                f"AI API HTTP 错误:\n"
                f"  状态码: {status}\n"
                f"  URL: {url}\n"
                f"  响应内容: {body}",
                exc_info=True
            )
            raise AIAPIError(friendly, status_code=status, response_body=body) from e
        except httpx.HTTPError as e:
            friendly = f"API 网络错误 [{type(e).__name__}]: {str(e)}"
            logger.error(
                f"AI API 调用失败:\n"
                f"  URL: {url}\n"
                f"  错误类型: {type(e).__name__}\n"
                f"  错误信息: {str(e)}",
                exc_info=True
            )
            raise AIAPIError(friendly, status_code=0, response_body="") from e

    async def analyze_market(
        self,
        current_price: float,
        price_history: List[Dict],
        user_positions: List[Dict],
        api_key: str,
        base_url: str = "",
        model: Optional[str] = None,
        symbol: str = "BTC/USDT"
    ) -> Dict:
        """
        市场分析

        Args:
            current_price: 当前价格
            price_history: 历史价格数据
            user_positions: 用户持仓信息
            api_key: API 密钥（必需）
            base_url: API 基础 URL
            model: 使用的模型

        Returns:
            分析结果 {trend, volatility, suggestion, reasoning}
        """
        # 构建市场分析提示词
        messages = [
            {
                "role": "system",
                "content": """你是一个专业的加密货币交易分析师。请基于提供的市场数据进行分析，
并给出交易建议。你的分析应该包括：
1. 市场趋势（上涨/下跌/震荡）
2. 波动率评估
3. 交易建议（做多/做空/观望）
4. 简要的分析理由

请以 JSON 格式返回结果：
{
    "trend": "uptrend/downtrend/sideways",
    "volatility": "low/medium/high",
    "suggestion": "long/short/hold",
    "reasoning": "分析理由"
}"""
            },
            {
                "role": "user",
                "content": f"""当前 {symbol} 价格: ${current_price:,.2f}

最近价格走势（最近10个数据点）:
{self._format_price_history(price_history[-10:])}

用户当前持仓:
{self._format_positions(user_positions)}

请进行市场分析并给出交易建议。"""
            }
        ]

        try:
            result = await self.chat_completion(messages, api_key=api_key, base_url=base_url, model=model)
            content = result["choices"][0]["message"]["content"]

            # 尝试解析 JSON
            import json
            try:
                analysis = json.loads(content)
            except json.JSONDecodeError:
                # 如果不是 JSON，返回文本分析
                analysis = {
                    "trend": "unknown",
                    "volatility": "unknown",
                    "suggestion": "hold",
                    "reasoning": content
                }

            return analysis

        except Exception as e:
            logger.error(f"市场分析失败: {e}")
            return {
                "trend": "unknown",
                "volatility": "unknown",
                "suggestion": "hold",
                "reasoning": f"分析失败: {str(e)}"
            }

    async def get_trading_advice(
        self,
        market_data: Dict,
        user_balance: float,
        api_key: str,
        base_url: str = "",
        risk_tolerance: str = "medium",
        model: Optional[str] = None
    ) -> Dict:
        """
        获取交易建议

        Args:
            market_data: 市场数据
            user_balance: 用户余额
            api_key: API 密钥（必需）
            base_url: API 基础 URL
            risk_tolerance: 风险承受能力 (low/medium/high)
            model: 使用的模型

        Returns:
            交易建议
        """
        messages = [
            {
                "role": "system",
                "content": """你是一个专业的加密货币交易顾问。基于用户的资金和风险偏好，
给出具体的交易建议。建议应包括：
1. 是否开仓
2. 交易方向（做多/做空）
3. 建议仓位大小
4. 建议杠杆倍数
5. 止损建议

以 JSON 格式返回：
{
    "action": "open/hold/close",
    "direction": "long/short",
    "position_size": 0.01,
    "leverage": 3,
    "stop_loss": 0.05,
    "reasoning": "建议理由"
}"""
            },
            {
                "role": "user",
                "content": f"""市场状态:
当前价格: ${market_data.get('current_price', 0):,.2f}
趋势: {market_data.get('trend', 'unknown')}
波动率: {market_data.get('volatility', 'unknown')}

用户信息:
可用余额: ${user_balance:,.2f}
风险偏好: {risk_tolerance}

请给出交易建议。"""
            }
        ]

        try:
            result = await self.chat_completion(messages, api_key=api_key, base_url=base_url, model=model)
            content = result["choices"][0]["message"]["content"]

            import json
            try:
                advice = json.loads(content)
            except json.JSONDecodeError:
                advice = {
                    "action": "hold",
                    "direction": "long",
                    "position_size": 0,
                    "leverage": 1,
                    "stop_loss": 0,
                    "reasoning": content
                }

            return advice

        except Exception as e:
            logger.error(f"获取交易建议失败: {e}")
            return {
                "action": "hold",
                "reasoning": f"建议生成失败: {str(e)}"
            }

    async def list_models(self) -> List[Dict]:
        """
        获取可用模型列表

        Returns:
            模型列表
        """
        return [
            {
                "id": model_id,
                **model_info
            }
            for model_id, model_info in AVAILABLE_MODELS.items()
        ]

    def _format_price_history(self, history: List[Dict]) -> str:
        """格式化价格历史"""
        if not history:
            return "无历史数据"

        lines = []
        for item in history:
            price = item.get('price', 0)
            timestamp = item.get('timestamp', '')
            lines.append(f"  {timestamp}: ${price:,.2f}")

        return "\n".join(lines)

    def _format_positions(self, positions: List[Dict]) -> str:
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
                f"  {side} {quantity} BTC @ ${entry_price:,.2f} (盈亏: ${pnl:,.2f})"
            )

        return "\n".join(lines)


# 全局 AI 服务实例
ai_service = AIService()
