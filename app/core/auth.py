import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import SESSION_COOKIE_SECURE
from app.db.session import get_db
from app.models.auth_session import AuthSession
from app.models.user import User

AUTH_COOKIE = "auth_token"
AUTH_MAX_AGE = 24 * 60 * 60  # 登入憑證固定 24 小時有效，不因複製 Cookie 而延長。


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 600_000)
    return f"pbkdf2_sha256$600000${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt, digest = encoded.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        computed = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt), int(iterations)
        )
        return hmac.compare_digest(computed, bytes.fromhex(digest))
    except (ValueError, TypeError):
        return False


def csrf_token(request: Request) -> str:
    # 升級舊版簽章 Cookie 時，移除其中的 user_id；簽章 Cookie 不再提供登入權限。
    request.session.pop("user_id", None)
    if "csrf" not in request.session:
        request.session["csrf"] = secrets.token_urlsafe(32)
    return request.session["csrf"]


def verify_csrf(request: Request) -> None:
    supplied = request.headers.get("X-CSRF-Token")
    if not supplied or not hmac.compare_digest(supplied, csrf_token(request)):
        raise HTTPException(status_code=403, detail="無效的表單驗證碼")


def get_auth_session(request: Request, db: Session) -> AuthSession | None:
    token = request.cookies.get(AUTH_COOKIE)
    if not token:
        return None
    # 修改處：只用 Cookie 的雜湊查資料庫；撤銷或過期的憑證不能再登入。
    stored = db.scalar(select(AuthSession).where(AuthSession.token_hash == hashlib.sha256(token.encode()).hexdigest()))
    if stored is None or stored.expires_at <= datetime.now(timezone.utc).replace(tzinfo=None):
        return None
    return stored


def issue_auth_cookie(response: Response, db: Session, user: User) -> None:
    # 修改處：登入時產生全新隨機憑證；MySQL 不保存可直接拿來登入的原文。
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    # 修改處：登入時順手清理過期紀錄，避免憑證表無限制累積。
    db.execute(delete(AuthSession).where(AuthSession.expires_at <= now))
    token = secrets.token_urlsafe(32)
    db.add(AuthSession(
        token_hash=hashlib.sha256(token.encode()).hexdigest(),
        user_id=user.id,
        expires_at=now + timedelta(seconds=AUTH_MAX_AGE),
    ))
    db.commit()
    response.set_cookie(AUTH_COOKIE, token, max_age=AUTH_MAX_AGE, httponly=True, secure=SESSION_COOKIE_SECURE, samesite="lax")


def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    stored = get_auth_session(request, db)
    user = db.get(User, stored.user_id) if stored else None
    if user is None:
        raise HTTPException(status_code=401, detail="請先登入")
    return user
