"""init schema

Revision ID: 0001
Revises:
Create Date: 2026-02-26

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    trade_side = sa.Enum("LONG", "SHORT", "BUY", "SELL", name="trade_side")
    trade_type = sa.Enum("OPEN", "CLOSE", "LIQUIDATION", name="trade_type")
    trade_side.create(op.get_bind(), checkfirst=True)
    trade_type.create(op.get_bind(), checkfirst=True)

    # create_type=False: 枚举已手动创建，阻止 SQLAlchemy 重复创建
    ts = sa.Enum("LONG", "SHORT", "BUY", "SELL", name="trade_side", create_type=False)
    tt = sa.Enum("OPEN", "CLOSE", "LIQUIDATION", name="trade_type", create_type=False)

    op.create_table(
        "nt_users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("username", sa.String(50), nullable=False, unique=True),
        sa.Column("password", sa.String(100), nullable=False),
        sa.Column("balance", sa.Float, nullable=False, server_default="10000.0"),
        sa.Column("initial_balance", sa.Float, nullable=False, server_default="10000.0"),
        sa.Column("ai_api_key", sa.String(200)),
        sa.Column("ai_base_url", sa.String(200)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("idx_nt_users_username", "nt_users", ["username"])

    op.create_table(
        "nt_positions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("nt_users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("side", ts, nullable=False),
        sa.Column("entry_price", sa.Float, nullable=False),
        sa.Column("quantity", sa.Float, nullable=False),
        sa.Column("leverage", sa.Integer, nullable=False, server_default="1"),
        sa.Column("margin", sa.Float, nullable=False),
        sa.Column("unrealized_pnl", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("is_open", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("liquidation_price", sa.Float),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("closed_at", sa.DateTime(timezone=True)),
    )
    op.create_index("idx_nt_positions_user_id", "nt_positions", ["user_id"])
    op.create_index("idx_nt_positions_is_open", "nt_positions", ["is_open"])

    op.create_table(
        "nt_trades",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("nt_users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("side", ts, nullable=False),
        sa.Column("price", sa.Float, nullable=False),
        sa.Column("quantity", sa.Float, nullable=False),
        sa.Column("leverage", sa.Integer, nullable=False, server_default="1"),
        sa.Column("pnl", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("trade_type", tt, nullable=False),
        sa.Column("market_data", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("idx_nt_trades_user_id", "nt_trades", ["user_id"])
    op.create_index("idx_nt_trades_created_at", "nt_trades", ["created_at"])

    op.create_table(
        "nt_prompt_configs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("nt_users.id", ondelete="CASCADE")),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("prompt_text", sa.Text, nullable=False),
        sa.Column("symbol", sa.String(20), nullable=False, server_default="BTC/USDT"),
        sa.Column("ai_model", sa.String(50), nullable=False, server_default="claude-4.5-opus"),
        sa.Column("execution_interval", sa.Integer, nullable=False, server_default="60"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("last_executed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("idx_nt_prompt_configs_name", "nt_prompt_configs", ["name"])
    op.create_index("idx_nt_prompt_configs_user_id", "nt_prompt_configs", ["user_id"])

    op.create_table(
        "nt_market_prices",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("price", sa.Float, nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("idx_nt_market_prices_symbol", "nt_market_prices", ["symbol"])
    op.create_index("idx_nt_market_prices_timestamp", "nt_market_prices", ["timestamp"])

    op.create_table(
        "nt_asset_history",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("nt_users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("total_assets", sa.Float, nullable=False),
        sa.Column("balance", sa.Float, nullable=False),
        sa.Column("position_value", sa.Float, nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("idx_nt_asset_history_user_time", "nt_asset_history", ["user_id", "timestamp"])

    op.create_table(
        "nt_ai_decision_logs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("nt_users.id", ondelete="CASCADE")),
        sa.Column("prompt_name", sa.String(100), nullable=False),
        sa.Column("market_context", sa.Text),
        sa.Column("ai_reasoning", sa.Text),
        sa.Column("decision", sa.String(20), nullable=False),
        sa.Column("action_taken", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("idx_nt_ai_decision_logs_user_id", "nt_ai_decision_logs", ["user_id"])
    op.create_index("idx_nt_ai_decision_logs_created_at", "nt_ai_decision_logs", ["created_at"])

    op.create_table(
        "nt_ai_conversations",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("nt_users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("idx_nt_ai_conversations_user_id", "nt_ai_conversations", ["user_id"])
    op.create_index("idx_nt_ai_conversations_created_at", "nt_ai_conversations", ["created_at"])


def downgrade() -> None:
    op.drop_table("nt_ai_conversations")
    op.drop_table("nt_ai_decision_logs")
    op.drop_table("nt_asset_history")
    op.drop_table("nt_market_prices")
    op.drop_table("nt_prompt_configs")
    op.drop_table("nt_trades")
    op.drop_table("nt_positions")
    op.drop_table("nt_users")
    sa.Enum(name="trade_type").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="trade_side").drop(op.get_bind(), checkfirst=True)
