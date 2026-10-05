from pydantic import BaseModel, ConfigDict, Field, field_validator


class TodoCreate(BaseModel):
    """新增任務的請求格式；id 由資料庫產生，完成狀態預設為否。"""

    title: str = Field(min_length=1, max_length=255)
    completed: bool = False

    @field_validator("title")
    @classmethod
    def clean_title(cls, value: str) -> str:
        # 去掉前後空白，避免將只有空白的字串寫入資料庫。
        value = value.strip()
        if not value:
            raise ValueError("任務名稱不可空白")
        return value


class TodoUpdate(BaseModel):
    """PATCH 僅修改送出的欄位，因此欄位在模型中可省略。"""

    title: str | None = Field(default=None, min_length=1, max_length=255)
    completed: bool | None = None

    @field_validator("title")
    @classmethod
    def clean_title(cls, value: str | None) -> str:
        # 可省略 title，但若明確提供 null 或空白則不能覆寫既有名稱。
        if value is None or not value.strip():
            raise ValueError("任務名稱不可空白")
        return value.strip()

    @field_validator("completed")
    @classmethod
    def validate_completed(cls, value: bool | None) -> bool:
        # completed 可省略；明確傳 null 不能覆寫資料庫的布林值。
        if value is None:
            raise ValueError("完成狀態不可為空")
        return value


class TodoResponse(BaseModel):
    """API 回傳格式；from_attributes 允許直接將 ORM 物件序列化。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    completed: bool
