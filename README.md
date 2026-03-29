# focus-log-BE

## Tech Stack
* **Backend Framework**: FastAPI
* **Database**: MariaDB
* **Language**: Python 3.10
* **Server**: Uvicorn
* **DB Driver**: PyMySQL

---

## Files

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
        └── study.py
```

---

## How to Run

### 1. Activate virtual environment

```bash
mkvirtualenv -p python3.10 focus-log-be
workon focus-log-be
```

---

### 2. Install packages

```bash
pip install -r requirements.txt
```

---

### 3. Set .env

```env
DB_HOST=your_host
DB_PORT=your_port
DB_USER=your_user
DB_PASSWORD=your_password
DB_NAME=your_db_name
```

---

### 4. Run FastAPI

```bash
python -m uvicorn main:app --reload
```

---

### 5. Check `/docs`

```text
http://127.0.0.1:8000/docs
```

## Progress

* [x] DB 연동 완료
* [x] Study Start API
* [x] Study Stop API
* [ ] Records API
* [ ] Ranking API
* [ ] Authentication

---
