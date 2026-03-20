import os
import unittest

os.environ["DATABASE_URL"] = "sqlite:///./test_open_source.db"
os.environ["DISABLE_SCHEDULER"] = "true"
os.environ["SECRET_KEY"] = "test-secret-key"

from backend.services.ai_service import AIService


class AIServiceTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_list_models_contains_default_model(self):
        models = await AIService().list_models()
        model_ids = {model["id"] for model in models}
        self.assertIn("claude-4.5-opus", model_ids)

    async def test_analyze_market_falls_back_for_non_json(self):
        service = AIService()

        async def fake_chat_completion(*args, **kwargs):
            return {"choices": [{"message": {"content": "市场震荡，建议观望"}}]}

        service.chat_completion = fake_chat_completion
        result = await service.analyze_market(
            current_price=50000.0,
            price_history=[],
            user_positions=[],
            api_key="test-key",
            base_url="https://example.com",
        )

        self.assertEqual(result["suggestion"], "hold")
        self.assertIn("市场震荡", result["reasoning"])


if __name__ == "__main__":
    unittest.main()
