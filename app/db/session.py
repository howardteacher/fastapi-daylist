from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import DATABASE_URL

# 借出連線前先檢查是否有效，並定期回收 MySQL 的閒置連線。
engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=3600)
# SessionLocal 是工廠；每個請求都要建立自己的 Session，不要共用同一個。
SessionLocal = sessionmaker(bind=engine, autoflush=False)


def get_db() -> Generator[Session, None, None]:
    """透過 FastAPI Depends 提供 Session，請求結束後自動關閉。"""
    with SessionLocal() as db:
        yield db
