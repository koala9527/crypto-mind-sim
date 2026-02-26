"""add HOLD and ERROR to tradetype enum

Revision ID: 0003
Revises: 0002
Create Date: 2026-02-26

"""
from typing import Sequence, Union
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE tradetype ADD VALUE IF NOT EXISTS 'HOLD'")
    op.execute("ALTER TYPE tradetype ADD VALUE IF NOT EXISTS 'ERROR'")


def downgrade() -> None:
    # PostgreSQL 不支持直接删除枚举值，downgrade 为空操作
    pass
