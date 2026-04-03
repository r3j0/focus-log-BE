from pydantic import BaseModel
from typing import Literal


class StudyUserRequest(BaseModel):
    user_id: int


class UserRecordRequest(BaseModel):
    user_id: int
    date: str | None = None


RankRange = Literal["today", "week", "month"]


class RankItem(BaseModel):
    rank: int
    user_id: int
    nickname: str
    total_duration_seconds: int
    is_studying: bool


class RankResponse(BaseModel):
    range: RankRange
    ranks: list[RankItem]
