"""保留舊版啟動入口，讓 uvicorn main:app 與 python main.py 仍可使用。"""

from app.main import app


if __name__ == "__main__":
    import uvicorn

    # 開發模式會監看程式碼異動；正式部署可改用 README 的 uvicorn 指令。
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
