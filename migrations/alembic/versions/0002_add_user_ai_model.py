"""add user ai_model column

Revision ID: 0002
Revises: 0001
Create Date: 2026-02-26

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "nt_users",
        sa.Column("ai_model", sa.String(100), nullable=True, server_default="claude-4.5-opus"),
    )


def downgrade() -> None:
    op.drop_column("nt_users", "ai_model")
