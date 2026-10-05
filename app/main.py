from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine
from starlette.middleware.sessions import SessionMiddleware

from app.api.todos import router as todos_router
from app.api.auth import router as auth_router
from app.db.base import Base
from app.db.session import engine
from app.models import AuthSession, Todo, User  # noqa: F401 - 登記所有資料表
from app.core.config import SESSION_COOKIE_SECURE, SESSION_SECRET_KEY
from app.web.routes import router as web_router


def prepare_database(db_engine: Engine) -> None:
    # 先替舊版 todos 加入歸屬欄位，再建立新表及索引；舊任務暫不屬於任何使用者。
    inspector = inspect(db_engine)
    if inspector.has_table("todos") and "owner_id" not in {
        column["name"] for column in inspector.get_columns("todos")
    }:
        with db_engine.begin() as connection:
            connection.execute(text("ALTER TABLE todos ADD COLUMN owner_id INTEGER NULL"))
    # 修改處：既有資料庫也會自動建立 auth_sessions，不會清除 users/todos。
    Base.metadata.create_all(bind=db_engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    prepare_database(engine)
    yield


app = FastAPI(title="Todo 任務清單", lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET_KEY, same_site="lax", https_only=SESSION_COOKIE_SECURE)
# API 與首頁路由分開管理；CSS/JS 由 FastAPI 提供靜態檔案。
app.include_router(todos_router)
app.include_router(auth_router)
app.include_router(web_router)
app.mount(
    "/static",
    StaticFiles(directory=str(Path(__file__).resolve().parent / "static")),
    name="static",
)
