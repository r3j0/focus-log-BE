# focus-log-BE

focus-log 백엔드 API 서버입니다. FastAPI + MariaDB 기반으로 공부 세션 기록, 개인 기록 조회, 랭킹 조회 기능을 제공합니다.

## Tech Stack
- **Backend Framework**: FastAPI
- **Database**: MariaDB
- **Language**: Python 3.10+
- **Server**: Uvicorn
- **DB Driver**: PyMySQL

---

## Project Structure

```text
focus-log-BE/
├── README.md
├── .env
├── requirements.txt
├── main.py
└── app/
    ├── __init__.py
    ├── database.py
    ├── schemas.py
    └── routers/
        ├── __init__.py
        ├── study.py
        ├── user.py
        └── rank.py
```

---

## How to Run

### 1. Create and activate venv

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure `.env`

```env
DB_HOST=your_host
DB_PORT=3306
DB_USER=your_user
DB_PASSWORD=your_password
DB_NAME=your_db_name
```

### 4. Run server

```bash
python3 -m uvicorn main:app --reload
```

### 5. API docs

```text
http://127.0.0.1:8000/docs
```

---

## API Endpoints

### 1) Study start
- `POST /study/start`
- Request body:

```json
{
  "user_id": 1
}
```

### 2) Study stop
- `POST /study/stop`
- Request body:

```json
{
  "user_id": 1
}
```

### 3) User daily record
- `POST /user/record`
- Request body (`date`는 선택):

```json
{
  "user_id": 1,
  "date": "2026-04-03"
}
```

### 4) Rank by period
- `GET /rank?range=today`
- `GET /rank?range=week`
- `GET /rank?range=month`

응답의 `ranks` 항목은 아래 필드를 포함합니다.
- `rank`: 동률은 같은 순위(경쟁 순위, 예: `1,1,3`)
- `user_id`
- `nickname`
- `total_duration_seconds`
- `is_studying`: 현재 활성 세션(`ended_at IS NULL`) 존재 여부

랭킹 합계에는 다음이 포함됩니다.
- 종료된 세션의 `duration_seconds`
- 활성 세션의 진행 시간(`started_at`부터 조회 시점까지), 단 선택 기간 경계 이전 시작분은 기간 내 구간만 반영

---

## Feature Status

- [x] B-01 기초 베이스 애플리케이션 실행 및 빌드
- [x] B-02 데이터베이스 연결
- [x] B-03 공부 시작 및 종료 상태 저장
- [x] B-04 유저 공부 기록 조회
- [x] B-05 서버 랭킹 조회
- [ ] B-06 닉네임 기반 로그인
