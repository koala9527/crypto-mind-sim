"""数据库连接和会话管理。"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.core.config import settings
from backend.core.models import Base


db_url = settings.DATABASE_URL

if not db_url.lower().startswith("sqlite"):
    raise RuntimeError(
        "CryptoMindSim 当前仅支持 SQLite，请将 DATABASE_URL 设置为 sqlite:///./neotrade.db。"
    )

engine_kwargs = {
    "echo": False,
    "pool_pre_ping": True,
    "connect_args": {"check_same_thread": False},
}

engine = create_engine(db_url, **engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """初始化数据库并创建表结构。"""
    Base.metadata.create_all(bind=engine)


def get_db():
    """依赖注入：获取数据库会话。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
