import os
import unittest

os.environ["DATABASE_URL"] = "sqlite:///./test_open_source.db"
os.environ["DISABLE_SCHEDULER"] = "true"
os.environ["SECRET_KEY"] = "test-secret-key"

from fastapi.testclient import TestClient

from backend.core.database import SessionLocal, engine
from backend.core.main import app
from backend.core.models import Base, Position, Trade, TradeSide, TradeType, User
from backend.engine.engine import trading_engine


Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)
trading_engine.fetch_current_price = lambda symbol=None: 50000.0


def register_payload(username: str, password: str = "test1234"):
    return {
        "username": username,
        "password": password,
        "ai_api_key": f"sk-{username}-demo-key",
        "ai_base_url": "https://api.openai.com/v1",
        "ai_model": "claude-4.5-opus",
    }


class DeleteUserTestCase(unittest.TestCase):
    def setUp(self):
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        trading_engine.fetch_current_price = lambda symbol=None: 50000.0
        self.client = TestClient(app)
        self.other_client = TestClient(app)

    def tearDown(self):
        self.client.close()
        self.other_client.close()

    def test_delete_user_clears_account_and_cookie(self):
        register = self.client.post(
            "/api/register",
            json=register_payload("alice"),
        )
        self.assertEqual(register.status_code, 201)
        user_id = register.json()["id"]

        position = self.client.post(
            f"/api/users/{user_id}/positions",
            json={"side": "LONG", "leverage": 2, "quantity": 0.01},
        )
        self.assertEqual(position.status_code, 201)

        delete_response = self.client.delete(f"/api/users/{user_id}")
        self.assertEqual(delete_response.status_code, 200)

        follow_up = self.client.get(f"/api/users/{user_id}")
        self.assertEqual(follow_up.status_code, 401)

        with SessionLocal() as db:
            self.assertIsNone(db.query(User).filter(User.id == user_id).first())

    def test_user_cannot_read_other_user_data(self):
        alice = self.client.post(
            "/api/register",
            json=register_payload("alice"),
        ).json()
        bob = self.other_client.post(
            "/api/register",
            json=register_payload("bob", "test5678"),
        ).json()

        forbidden = self.client.get(f"/api/users/{bob['id']}")
        self.assertEqual(forbidden.status_code, 403)

        own = self.client.get(f"/api/users/{alice['id']}")
        self.assertEqual(own.status_code, 200)

    def test_trade_detail_contains_beginner_fields(self):
        register = self.client.post(
            "/api/register",
            json=register_payload("carol"),
        )
        self.assertEqual(register.status_code, 201)
        user_id = register.json()["id"]

        open_response = self.client.post(
            f"/api/users/{user_id}/positions",
            json={"side": "LONG", "leverage": 2, "quantity": 0.01},
        )
        self.assertEqual(open_response.status_code, 201)

        trades = self.client.get(f"/api/users/{user_id}/trades")
        self.assertEqual(trades.status_code, 200)
        trade_id = trades.json()["trades"][0]["id"]

        detail = self.client.get(f"/api/trades/{trade_id}")
        self.assertEqual(detail.status_code, 200)
        payload = detail.json()

        self.assertEqual(payload["execution_source"], "MANUAL")
        self.assertEqual(payload["position_side"], "LONG")
        self.assertGreater(payload["margin_used"], 0)
        self.assertGreaterEqual(payload["fee_paid"], 0)
        self.assertIn("balance_before", payload)
        self.assertIn("balance_after", payload)

    def test_position_detail_contains_beginner_fields(self):
        register = self.client.post(
            "/api/register",
            json=register_payload("dave"),
        )
        self.assertEqual(register.status_code, 201)
        user_id = register.json()["id"]

        open_response = self.client.post(
            f"/api/users/{user_id}/positions",
            json={"side": "LONG", "leverage": 4, "quantity": 0.01},
        )
        self.assertEqual(open_response.status_code, 201)
        position_id = open_response.json()["id"]

        trading_engine.fetch_current_price = lambda symbol=None: 51000.0

        positions = self.client.get(f"/api/users/{user_id}/positions")
        self.assertEqual(positions.status_code, 200)
        summary = positions.json()[0]
        self.assertEqual(summary["current_price"], 51000.0)
        self.assertIn("roi_pct", summary)
        self.assertIn("risk_level", summary)
        self.assertIn("holding_seconds", summary)

        detail = self.client.get(f"/api/positions/{position_id}")
        self.assertEqual(detail.status_code, 200)
        payload = detail.json()

        self.assertEqual(payload["current_price"], 51000.0)
        self.assertGreater(payload["roi_pct"], 0)
        self.assertIn(payload["risk_level"], ["LOW", "MEDIUM", "HIGH"])
        self.assertIn("break_even_price", payload)
        self.assertIn("status_text", payload)
        self.assertIn("position_explanation", payload)
        self.assertIn("next_action_tip", payload)

    def test_register_saves_ai_config_with_account(self):
        register = self.client.post(
            "/api/register",
            json=register_payload("erin"),
        )
        self.assertEqual(register.status_code, 201)
        user_id = register.json()["id"]

        ai_config = self.client.get(f"/api/users/{user_id}/ai-config")
        self.assertEqual(ai_config.status_code, 200)
        payload = ai_config.json()

        self.assertTrue(payload["configured"])
        self.assertEqual(payload["base_url"], "https://api.openai.com/v1")
        self.assertEqual(payload["ai_model"], "claude-4.5-opus")
        self.assertTrue(payload["api_key_masked"])

    def test_error_trade_returns_error_message(self):
        register = self.client.post(
            "/api/register",
            json=register_payload("frank"),
        )
        self.assertEqual(register.status_code, 201)
        user_id = register.json()["id"]

        with SessionLocal() as db:
            trade = Trade(
                user_id=user_id,
                symbol="BTC/USDT",
                side=TradeSide.BUY,
                price=0.0,
                quantity=0.0,
                leverage=1,
                trade_type=TradeType.ERROR,
                market_data='{"error":"AI 返回格式错误","exception":"JSONDecodeError"}',
            )
            db.add(trade)
            db.commit()
            db.refresh(trade)
            trade_id = trade.id

        detail = self.client.get(f"/api/trades/{trade_id}")
        self.assertEqual(detail.status_code, 200)
        payload = detail.json()

        self.assertEqual(payload["trade_type"], "ERROR")
        self.assertEqual(payload["error_message"], "AI 返回格式错误")
        self.assertIn("market_data", payload)

    def test_bulk_close_positions_by_symbols(self):
        register = self.client.post(
            "/api/register",
            json=register_payload("gina"),
        )
        self.assertEqual(register.status_code, 201)
        user_id = register.json()["id"]

        btc_position = self.client.post(
            f"/api/users/{user_id}/positions",
            json={"symbol": "BTC/USDT", "side": "LONG", "leverage": 2, "quantity": 0.01},
        )
        self.assertEqual(btc_position.status_code, 201)

        eth_position = self.client.post(
            f"/api/users/{user_id}/positions",
            json={"symbol": "ETH/USDT", "side": "LONG", "leverage": 2, "quantity": 0.02},
        )
        self.assertEqual(eth_position.status_code, 201)

        bulk_close = self.client.post(
            f"/api/users/{user_id}/positions/close-all",
            json={"symbols": ["BTC/USDT"]},
        )
        self.assertEqual(bulk_close.status_code, 200)
        payload = bulk_close.json()

        self.assertEqual(payload["closed_count"], 1)
        self.assertEqual(payload["requested_symbols"], ["BTC/USDT"])

        with SessionLocal() as db:
            btc = db.query(Position).filter(Position.user_id == user_id, Position.symbol == "BTC/USDT").first()
            eth = db.query(Position).filter(Position.user_id == user_id, Position.symbol == "ETH/USDT").first()

            self.assertFalse(btc.is_open)
            self.assertTrue(eth.is_open)

            close_trade = (
                db.query(Trade)
                .filter(Trade.user_id == user_id, Trade.trade_type == TradeType.CLOSE, Trade.symbol == "BTC/USDT")
                .first()
            )
            self.assertIsNotNone(close_trade)
            self.assertEqual(close_trade.close_reason, "SYMBOL_SWITCH_CLOSE")


if __name__ == "__main__":
    unittest.main()

