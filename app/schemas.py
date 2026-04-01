from pydantic import BaseModel
class StudyUserRequest(BaseModel):
    user_id: int

class UserRecordRequest(BaseModel):
    user_id: int
    date: str | None = None