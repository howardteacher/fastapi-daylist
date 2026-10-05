import os
import secrets
from pathlib import Path

from dotenv import load_dotenv


# 從專案根目錄讀取 .env；已設定的環境變數仍優先。
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("請在專案根目錄的 .env 設定 DATABASE_URL，或設定 DATABASE_URL 環境變數")

# 此金鑰僅簽署 CSRF 用的 Cookie；登入憑證由 MySQL 的 auth_sessions 驗證。
SESSION_SECRET_KEY = os.getenv("SESSION_SECRET_KEY") or secrets.token_urlsafe(32)
SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"
