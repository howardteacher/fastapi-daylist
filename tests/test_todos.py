import pytest
import re
import hashlib
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.core.auth import AUTH_COOKIE
from app.main import app, prepare_database
from app.models.auth_session import AuthSession


@pytest.fixture
def client():
    # 使用記憶體 SQLite 隔離各項測試，避免測試誤動到真實 MySQL 資料。
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    def override_db():
        with session_factory() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    try:
        # TestClient without a context manager does not run the MySQL startup lifespan.
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def csrf(client, path="/login"):
    page = client.get(path)
    return re.search(r'<meta name="csrf-token" content="([^"]+)"', page.text).group(1)


def register(client, username="alice", password="password123"):
    token = csrf(client)
    result = client.post("/auth/register", json={"username": username, "password": password}, headers={"X-CSRF-Token": token})
    assert result.status_code == 200
    return {"X-CSRF-Token": csrf(client, "/")}


def test_todo_crud(client):
    # 驗證首頁、靜態資源，以及任務新增到刪除的完整流程。
    headers = register(client)
    assert client.get("/").status_code == 200
    assert client.get("/static/js/app.js").status_code == 200

    created = client.post("/todos/", json={"title": "  學習 FastAPI  "}, headers=headers)
    assert created.status_code == 201
    todo = created.json()
    assert todo == {"id": 1, "title": "學習 FastAPI", "completed": False}
    assert client.get("/todos/1").json() == todo
    assert client.get("/todos/").json() == [todo]

    updated = client.patch("/todos/1", json={"completed": True, "title": "完成練習"}, headers=headers)
    assert updated.status_code == 200
    assert updated.json() == {"id": 1, "title": "完成練習", "completed": True}
    assert client.delete("/todos/1", headers=headers).status_code == 204
    assert client.get("/todos/").json() == []
    assert client.get("/todos/1").status_code == 404
    assert client.patch("/todos/1", json={"completed": False}, headers=headers).status_code == 404
    assert client.delete("/todos/1", headers=headers).status_code == 404


def test_validation_and_pagination(client):
    # 確認不合法資料會被拒絕，分頁也維持新任務在前的順序。
    headers = register(client)
    for title in ("   ", "x" * 256):
        assert client.post("/todos/", json={"title": title}, headers=headers).status_code == 422
    assert client.post("/todos/", json={"title": "第一件"}, headers=headers).status_code == 201
    assert client.post("/todos/", json={"title": "第二件"}, headers=headers).status_code == 201
    assert [item["title"] for item in client.get("/todos/?limit=1").json()] == ["第二件"]
    assert [item["title"] for item in client.get("/todos/?skip=1&limit=1").json()] == ["第一件"]
    assert client.patch("/todos/1", json={"title": "  "}, headers=headers).status_code == 422
    assert client.patch("/todos/1", json={"completed": None}, headers=headers).status_code == 422
    assert client.get("/todos/?limit=0").status_code == 422


def test_auth_and_isolation(client):
    assert client.get("/", follow_redirects=False).headers["location"] == "/login"
    assert client.get("/todos/").status_code == 401
    assert client.post("/todos/", json={"title": "未登入"}).status_code == 401
    token = csrf(client)
    assert client.post("/auth/register", json={"username": "alice", "password": "password123"}).status_code == 403
    alice = register(client)
    assert client.post("/todos/", json={"title": "Alice 的任務"}).status_code == 403
    assert client.post("/todos/", json={"title": "Alice 的任務"}, headers=alice).status_code == 201
    assert client.post("/auth/register", json={"username": "alice", "password": "password123"}, headers=alice).status_code == 409
    assert client.post("/auth/logout", headers=alice).status_code == 200
    assert client.get("/todos/").status_code == 401
    token = csrf(client)
    assert client.post("/auth/login", json={"username": "alice", "password": "wrongpass"}, headers={"X-CSRF-Token": token}).status_code == 401
    assert client.post("/auth/login", json={"username": "alice", "password": "password123"}, headers={"X-CSRF-Token": token}).status_code == 200
    assert client.get("/todos/1").status_code == 200
    assert client.post("/auth/logout", headers={"X-CSRF-Token": csrf(client, "/")}).status_code == 200
    bob = register(client, "bob")
    assert client.get("/todos/").json() == []
    assert client.get("/todos/1").status_code == 404
    assert client.patch("/todos/1", json={"completed": True}, headers=bob).status_code == 404
    assert client.delete("/todos/1", headers=bob).status_code == 404


def test_existing_todos_survive_upgrade():
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE todos (id INTEGER PRIMARY KEY, title VARCHAR(255) NOT NULL, completed BOOLEAN NOT NULL)"))
        connection.execute(text("INSERT INTO todos (id, title, completed) VALUES (1, '舊任務', 0)"))
    prepare_database(engine)
    prepare_database(engine)
    assert "owner_id" in {column["name"] for column in inspect(engine).get_columns("todos")}
    assert inspect(engine).has_table("auth_sessions")
    with engine.connect() as connection:
        assert connection.execute(text("SELECT title, owner_id FROM todos WHERE id = 1")).one() == ("舊任務", None)
    engine.dispose()


def test_stolen_cookie_revoked_on_logout(client):
    headers = register(client)
    stolen = client.cookies.get(AUTH_COOKIE)
    assert stolen
    # 修改處：檢查資料庫僅有雜湊，複製的 Cookie 登出前有效、登出後立即無效。
    with next(app.dependency_overrides[get_db]()) as db:
        stored = db.query(AuthSession).one()
        assert stored.token_hash == hashlib.sha256(stolen.encode()).hexdigest()
        assert stolen != stored.token_hash
    other = TestClient(app)
    other.cookies.set(AUTH_COOKIE, stolen)
    assert other.get("/").status_code == 200
    assert client.post("/auth/logout", headers=headers).status_code == 200
    assert other.get("/todos/").status_code == 401
    assert other.get("/", follow_redirects=False).headers["location"] == "/login"


def test_expired_and_rotated_sessions(client):
    register(client)
    old_token = client.cookies.get(AUTH_COOKIE)
    token = csrf(client, "/")
    assert client.post("/auth/login", json={"username": "alice", "password": "password123"}, headers={"X-CSRF-Token": token}).status_code == 200
    assert client.cookies.get(AUTH_COOKIE) != old_token
    other = TestClient(app)
    other.cookies.set(AUTH_COOKIE, old_token)
    assert other.get("/todos/").status_code == 401
    with next(app.dependency_overrides[get_db]()) as db:
        stored = db.query(AuthSession).one()
        stored.expires_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=1)
        db.commit()
    assert client.get("/todos/").status_code == 401


def test_auth_cookie_flags(client):
    token = csrf(client)
    response = client.post("/auth/register", json={"username": "alice", "password": "password123"}, headers={"X-CSRF-Token": token})
    assert response.status_code == 200
    cookie = response.headers["set-cookie"]
    assert "auth_token=" in cookie
    assert "httponly" in cookie.lower()
    assert "samesite=lax" in cookie.lower()
    assert "max-age=86400" in cookie.lower()
