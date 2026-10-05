from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.auth import AUTH_COOKIE, get_auth_session, hash_password, issue_auth_cookie, verify_csrf, verify_password
from app.core.config import SESSION_COOKIE_SECURE
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import Credentials

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", dependencies=[Depends(verify_csrf)])
def register(data: Credentials, request: Request, response: Response, db: Session = Depends(get_db)):
    user = User(username=data.username, password_hash=hash_password(data.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="帳號已存在") from None
    db.refresh(user)
    previous = get_auth_session(request, db)
    if previous:
        db.delete(previous)
    request.session.clear()
    # 修改處：註冊完成也改發可由資料庫撤銷的登入憑證。
    issue_auth_cookie(response, db, user)
    return {"username": user.username}


@router.post("/login", dependencies=[Depends(verify_csrf)])
def login(data: Credentials, request: Request, response: Response, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.username == data.username))
    if user is None or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="帳號或密碼錯誤")
    # 修改處：同一瀏覽器重新登入時撤銷舊憑證，避免換帳號後舊 Cookie 仍可用。
    previous = get_auth_session(request, db)
    if previous:
        db.delete(previous)
    request.session.clear()
    # 修改處：每次登入換發新的憑證，不再將 user_id 存進簽章 Cookie。
    issue_auth_cookie(response, db, user)
    return {"username": user.username}


@router.post("/logout", dependencies=[Depends(verify_csrf)])
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    # 修改處：登出先刪除 MySQL 紀錄，已被複製的舊 Cookie 也會立即失效。
    stored = get_auth_session(request, db)
    if stored:
        db.delete(stored)
        db.commit()
    response.delete_cookie(AUTH_COOKIE, secure=SESSION_COOKIE_SECURE, samesite="lax")
    request.session.clear()
    return {"message": "已登出"}
