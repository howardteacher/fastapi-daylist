from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.todo import Todo
from app.schemas.todo import TodoCreate, TodoUpdate


def list_todos(db: Session, owner_id: int, skip: int, limit: int) -> list[Todo]:
    # 依 id 反向排序，新建立的任務在上方；skip/limit 對應 API 分頁參數。
    return list(db.scalars(select(Todo).where(Todo.owner_id == owner_id).order_by(Todo.id.desc()).offset(skip).limit(limit)))


def get_todo(db: Session, todo_id: int, owner_id: int) -> Todo | None:
    # 找不到資料時回傳 None，交由 API 層決定 HTTP 404 回應。
    return db.scalar(select(Todo).where(Todo.id == todo_id, Todo.owner_id == owner_id))


def create_todo(db: Session, data: TodoCreate, owner_id: int) -> Todo:
    # 將已驗證的請求資料轉成 ORM 物件，提交後重新載入資料庫產生的 id。
    todo = Todo(**data.model_dump(), owner_id=owner_id)
    db.add(todo)
    db.commit()
    db.refresh(todo)
    return todo


def update_todo(db: Session, todo: Todo, data: TodoUpdate) -> Todo:
    # exclude_unset=True 可保留未出現在 PATCH 請求中的原始欄位。
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(todo, field, value)
    db.commit()
    db.refresh(todo)
    return todo


def delete_todo(db: Session, todo: Todo) -> None:
    db.delete(todo)
    db.commit()
