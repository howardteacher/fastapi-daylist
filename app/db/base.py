from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """所有資料表模型的共同基底，集中管理 SQLAlchemy metadata。"""

    pass
