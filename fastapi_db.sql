-- ==========================================
-- FastAPI Todo 專案資料庫
-- 資料庫名稱：fastapi_db
-- 資料表名稱：users、todos、auth_sessions
-- ==========================================

CREATE DATABASE IF NOT EXISTS fastapi_db
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

USE fastapi_db;

CREATE TABLE IF NOT EXISTS users (
    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL
);

-- 修改處：憑證原文只在 HttpOnly Cookie，資料庫儲存雜湊及到期時間。
CREATE TABLE IF NOT EXISTS auth_sessions (
    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    token_hash VARCHAR(64) NOT NULL UNIQUE,
    user_id INT NOT NULL,
    expires_at DATETIME NOT NULL,
    INDEX idx_auth_sessions_expires_at (expires_at),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS todos (
    id INT NOT NULL AUTO_INCREMENT,
    title VARCHAR(255) NOT NULL,
    completed BOOLEAN NOT NULL DEFAULT FALSE,
    owner_id INT NULL,

    PRIMARY KEY (id),
    INDEX idx_todos_title (title),
    INDEX idx_todos_owner_id (owner_id),
    FOREIGN KEY (owner_id) REFERENCES users(id)
);

-- 舊版 todos 沒有 owner_id 時，應用程式啟動會自動新增 nullable 欄位。
-- 舊任務不會自動分配給新帳號；請在註冊後用 SQL 指定歸屬。
