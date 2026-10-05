from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Todo(Base):
    """對應 MySQL 的 todos 資料表；欄位名稱與原有資料表相容。"""

    __tablename__ = "todos"

    # 自動遞增主鍵，供查詢、更新與刪除單筆任務使用。
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # 舊資料可保持 NULL，待管理者決定歸屬；新任務一定設定 owner_id。
    owner_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    owner = relationship("User", back_populates="todos")
