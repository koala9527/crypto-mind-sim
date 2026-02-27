"""
数据库连接和会话管理
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.core.config import settings
from backend.core.models import Base

# 创建数据库引擎
db_url = settings.DATABASE_URL
# psycopg3: 需要 postgresql+psycopg:// 前缀
if db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)

engine = create_engine(
    db_url,
    echo=False,
    pool_size=20,              # 增加连接池大小以支持多用户并发
    max_overflow=30,           # 增加溢出连接数
    pool_pre_ping=True,        # 检测断开的连接
    pool_recycle=3600,         # 1小时后回收连接，防止连接过期
    pool_timeout=60,           # 增加超时时间到60秒
    connect_args={
        "connect_timeout": 10,  # PostgreSQL 连接超时
        "options": "-c statement_timeout=30000"  # SQL 语句超时 30秒
    }
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """初始化数据库，创建所有表"""
    Base.metadata.create_all(bind=engine)


def get_db():
    """依赖注入：获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
