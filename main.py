from fastapi import FastAPI
from app.routers import study

app = FastAPI()

@app.get("/")
def root():
    return {"message": "FastAPI + MariaDB 연결 테스트 서버"}

app.include_router(study.router)