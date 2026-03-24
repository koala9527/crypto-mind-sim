import os
import unittest
from datetime import timedelta

os.environ["DATABASE_URL"] = "sqlite:///./test_open_source.db"
os.environ["DISABLE_SCHEDULER"] = "true"
os.environ["SECRET_KEY"] = "test-secret-key"

from fastapi.testclient import TestClient

from backend.core.database import SessionLocal, engine
from backend.core.main import app
from backend.core.models import AIDecisionLog, Base, PromptConfig, PromptRevisionHistory, get_local_time
from backend.engine.strategy_executor import count_prompt_optimization_decisions


def register_payload(username: str, password: str = "test1234"):
    return {
        "username": username,
        "password": password,
        "ai_api_key": f"sk-{username}-demo-key",
        "ai_base_url": "https://api.openai.com/v1",
        "ai_model": "claude-4.5-opus",
    }


class StrategyPromptOptimizationTestCase(unittest.TestCase):
    def setUp(self):
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()

    def test_create_strategy_with_prompt_optimization_fields(self):
        register = self.client.post("/api/register", json=register_payload("optim-alpha"))
        self.assertEqual(register.status_code, 201)
        user_id = register.json()["id"]

        strategies_response = self.client.get(f"/api/strategies?user_id={user_id}")
        self.assertEqual(strategies_response.status_code, 200)
        strategies = strategies_response.json()
        self.assertEqual(len(strategies), 1)
        strategy_id = strategies[0]["id"]

        response = self.client.put(
            f"/api/strategies/{strategy_id}?user_id={user_id}",
            json={
                "name": "自动修正策略",
                "description": "测试自动修正字段",
                "symbol": "BTC/USDT",
                "prompt_text": "你是一个激进但守纪律的交易员。",
                "base_prompt_text": "你是一个激进但守纪律的交易员。",
                "auto_optimize_prompt": True,
                "prompt_optimization_interval": 3,
                "prompt_optimization_include_hold": False,
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["auto_optimize_prompt"])
        self.assertEqual(payload["prompt_optimization_interval"], 3)
        self.assertFalse(payload["prompt_optimization_include_hold"])
        self.assertEqual(payload["base_prompt_text"], "你是一个激进但守纪律的交易员。")
        self.assertEqual(payload["prompt_revision_count"], 0)

        with SessionLocal() as db:
            history = db.query(PromptRevisionHistory).filter(PromptRevisionHistory.strategy_id == payload["id"]).all()
            self.assertEqual(len(history), 2)
            self.assertEqual(history[0].source, "CREATE")
            self.assertEqual(history[1].source, "MANUAL_UPDATE")

    def test_prompt_revision_history_endpoint_tracks_lifecycle(self):
        register = self.client.post("/api/register", json=register_payload("optim-history"))
        self.assertEqual(register.status_code, 201)
        user_id = register.json()["id"]

        strategies_response = self.client.get(f"/api/strategies?user_id={user_id}")
        self.assertEqual(strategies_response.status_code, 200)
        strategies = strategies_response.json()
        self.assertEqual(len(strategies), 1)
        strategy_id = strategies[0]["id"]
        initial_prompt_text = strategies[0]["prompt_text"]

        updated = self.client.put(
            f"/api/strategies/{strategy_id}?user_id={user_id}",
            json={
                "prompt_text": "手动更新后的提示词",
                "revision_source": "MANUAL_UPDATE",
            },
        )
        self.assertEqual(updated.status_code, 200)

        history_response = self.client.get(
            f"/api/strategies/{strategy_id}/prompt-revisions?user_id={user_id}&limit=20"
        )
        self.assertEqual(history_response.status_code, 200)
        payload = history_response.json()

        self.assertEqual(len(payload), 2)
        self.assertEqual(payload[0]["source"], "MANUAL_UPDATE")
        self.assertEqual(payload[1]["source"], "CREATE")
        self.assertEqual(payload[0]["previous_prompt_text"], initial_prompt_text)
        self.assertEqual(payload[0]["prompt_text"], "手动更新后的提示词")

    def test_count_prompt_optimization_decisions_respects_hold_switch(self):
        register = self.client.post("/api/register", json=register_payload("optim-beta"))
        self.assertEqual(register.status_code, 201)
        user_id = register.json()["id"]

        with SessionLocal() as db:
            strategy = PromptConfig(
                user_id=user_id,
                name="节奏策略",
                prompt_text="原始提示词",
                base_prompt_text="原始提示词",
                symbol="BTC/USDT",
                auto_optimize_prompt=True,
                prompt_optimization_interval=2,
                prompt_optimization_include_hold=False,
                last_prompt_optimized_at=get_local_time() - timedelta(minutes=5),
                is_active=True,
            )
            db.add(strategy)
            db.flush()

            db.add_all(
                [
                    AIDecisionLog(
                        user_id=user_id,
                        prompt_name="节奏策略",
                        decision="HOLD",
                        action_taken=False,
                    ),
                    AIDecisionLog(
                        user_id=user_id,
                        prompt_name="节奏策略",
                        decision="OPEN",
                        action_taken=True,
                    ),
                    AIDecisionLog(
                        user_id=user_id,
                        prompt_name="节奏策略",
                        decision="CLOSE",
                        action_taken=True,
                    ),
                ]
            )
            db.commit()
            db.refresh(strategy)

            without_hold = count_prompt_optimization_decisions(db, strategy)
            self.assertEqual(without_hold, 2)

            strategy.prompt_optimization_include_hold = True
            with_hold = count_prompt_optimization_decisions(db, strategy)
            self.assertEqual(with_hold, 3)


if __name__ == "__main__":
    unittest.main()
