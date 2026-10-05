from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.auth import csrf_token, get_auth_session
from app.db.session import get_db
from app.models.user import User

# 使用檔案所在位置尋找模板，避免從其他工作目錄啟動時找不到頁面。
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[1] / "templates"))
router = APIRouter()


@router.get("/", include_in_schema=False)
def home(request: Request, db: Session = Depends(get_db)):
    # 首頁由模板提供 HTML；任務資料在瀏覽器端透過 /todos/ API 取得。
    # 修改處：頁面與 API 共用資料庫 session 檢查，不相信舊版 Cookie 的 user_id。
    stored = get_auth_session(request, db)
    user = db.get(User, stored.user_id) if stored else None
    if user is None:
        return RedirectResponse("/login", status_code=303)
    return templates.TemplateResponse(request, "index.html", {"username": user.username, "csrf": csrf_token(request)})


@router.get("/login", include_in_schema=False)
def login_page(request: Request, db: Session = Depends(get_db)):
    stored = get_auth_session(request, db)
    if stored and db.get(User, stored.user_id) is not None:
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse(request, "login.html", {"csrf": csrf_token(request)})
