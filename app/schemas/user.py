from pydantic import BaseModel, Field


class Credentials(BaseModel):
    username: str = Field(pattern=r"^[A-Za-z0-9_]{3,50}$")
    password: str = Field(min_length=8, max_length=128)
