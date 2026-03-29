from pydantic import BaseModel

class StudyUserRequest(BaseModel):
    user_id: int