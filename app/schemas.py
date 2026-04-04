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


class AuthCredentialRequest(BaseModel):
    nickname: str
    password: str


class TokenRefreshRequest(BaseModel):
    refresh_token: str


class AuthTokenResponse(BaseModel):
    user_id: int
    nickname: str
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    access_expires_in: int


class RefreshTokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    access_expires_in: int
