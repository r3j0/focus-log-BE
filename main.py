from fastapi import FastAPI
from app.routers import auth, rank, study, user

app = FastAPI()

@app.get("/")
def root():
    return {"message": "FastAPI + MariaDB 연결 테스트 서버"}

app.include_router(study.router)
app.include_router(user.router)
app.include_router(rank.router)
app.include_router(auth.router)
