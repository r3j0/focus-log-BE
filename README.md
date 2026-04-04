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
├── migrations/
│   └── 20260404_b06_auth.sql
└── app/
    ├── __init__.py
    ├── auth_utils.py
    ├── database.py
    ├── schemas.py
    └── routers/
        ├── __init__.py
        ├── auth.py
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
JWT_ACCESS_SECRET=your_access_secret
JWT_REFRESH_SECRET=your_refresh_secret
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=14
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

### Auth (Public)

#### 1) Auth signup
- `POST /auth/signup`
- Request body:

```json
{
  "nickname": "user_nickname",
  "password": "user_password"
}
```

#### 2) Auth login
- `POST /auth/login`
- Request body:

```json
{
  "nickname": "user_nickname",
  "password": "user_password"
}
```

#### 3) Auth refresh
- `POST /auth/refresh`
- Request body:

```json
{
  "refresh_token": "..."
}
```

#### 4) Auth logout
- `POST /auth/logout`
- Request body:

```json
{
  "refresh_token": "..."
}
```

---

### Protected APIs (Access Token Required)

아래 API는 모두 `Authorization: Bearer <access_token>` 헤더가 필요합니다.

- Swagger(` /docs `) 사용 시:
  1. 우측 상단 `Authorize` 클릭
  2. `Bearer <access_token>` 입력
  3. `Authorize` 적용 후 요청 실행

#### 5) Study start
- `POST /study/start`
- Request body 없음
- 토큰의 `sub` 사용자로 시작 세션 생성

#### 6) Study stop
- `POST /study/stop`
- Request body 없음
- 토큰의 `sub` 사용자의 활성 세션 종료

#### 7) User daily record
- `POST /user/record`
- Request body (`date`는 선택):

```json
{
  "date": "2026-04-03"
}
```
- `user_id`는 요청 바디로 받지 않으며, 토큰 사용자 기준으로 조회

#### 8) Rank by period
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

## DB Migration

인증 기능(B-06)을 사용하려면 DB 마이그레이션을 먼저 적용해야 합니다.

```sql
SOURCE migrations/20260404_b06_auth.sql;
```

핵심 변경 사항:
- `users.password_hash` 추가
- `users.nickname` 유니크 제약
- `refresh_tokens` 테이블 추가

> 참고: 운영 환경에서는 `JWT_ACCESS_SECRET`, `JWT_REFRESH_SECRET`를 반드시 설정하세요.
