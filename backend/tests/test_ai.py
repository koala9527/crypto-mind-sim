"""
AI功能测试脚本
"""
import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.services.ai_service import ClaudeAIService
from backend.core.config import settings


async def test_market_analysis():
    """测试市场分析功能"""
    print("=" * 50)
    print("测试1: 市场分析功能")
    print("=" * 50)

    ai_service = ClaudeAIService()

    # 模拟价格数据
    price_history = [
        {"price": 43000, "timestamp": "2024-01-01 00:00:00"},
        {"price": 43200, "timestamp": "2024-01-01 01:00:00"},
        {"price": 43100, "timestamp": "2024-01-01 02:00:00"},
        {"price": 43500, "timestamp": "2024-01-01 03:00:00"},
        {"price": 43800, "timestamp": "2024-01-01 04:00:00"},
    ]

    result = await ai_service.analyze_market(
        symbol="BTC/USDT",
        current_price=43800.0,
        price_history=price_history,
        prompt_config="分析市场趋势，给出交易建议"
    )

    print(f"\n决策结果：")
    print(f"  动作: {result['decision']}")
    print(f"  信心度: {result['confidence']:.2f}")
    print(f"  建议杠杆: {result['suggested_leverage']}x")
    print(f"  建议数量: {result['suggested_quantity']} BTC")
    print(f"  理由: {result['reasoning']}")
    print()


async def test_chat():
    """测试对话功能"""
    print("=" * 50)
    print("测试2: AI对话功能")
    print("=" * 50)

    ai_service = ClaudeAIService()

    # 模拟用户上下文
    user_context = {
        "balance": 8500.50,
        "position_count": 2,
        "total_assets": 9200.00
    }

    # 对话历史
    conversation_history = [
        {"role": "user", "content": "当前市场趋势如何？"},
        {"role": "assistant", "content": "根据最近的价格走势，市场呈现上涨趋势..."},
    ]

    # 新的用户消息
    user_message = "我应该什么时候平仓？"

    response = await ai_service.chat(
        user_message=user_message,
        conversation_history=conversation_history,
        user_context=user_context
    )

    print(f"\n用户问题: {user_message}")
    print(f"AI回复: {response}")
    print()


async def test_api_connection():
    """测试API连接"""
    print("=" * 50)
    print("测试0: API连接测试")
    print("=" * 50)

    print(f"\nAPI配置信息：")
    print(f"  Base URL: {settings.ANTHROPIC_BASE_URL}")
    print(f"  Model: {settings.ANTHROPIC_MODEL}")
    print(f"  API Key (前10位): {settings.ANTHROPIC_AUTH_TOKEN[:10]}...")
    print()

    ai_service = ClaudeAIService()

    try:
        # 简单的连接测试
        response = await ai_service._call_api(
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=50
        )
        print("✓ API连接成功！")
        print(f"  响应内容: {response.get('content', [{}])[0].get('text', 'N/A')[:100]}")
    except Exception as e:
        print(f"✗ API连接失败: {e}")


async def main():
    """运行所有测试"""
    print("\n🤖 CryptoMindSim AI功能测试")
    print("=" * 50)
    print()

    try:
        # 测试0: API连接
        await test_api_connection()

        # 测试1: 市场分析
        await test_market_analysis()

        # 测试2: AI对话
        await test_chat()

        print("=" * 50)
        print("✓ 所有测试完成！")
        print("=" * 50)

    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
