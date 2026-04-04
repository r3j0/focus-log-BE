from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime
from zoneinfo import ZoneInfo

from app.auth_utils import get_current_user_id
from app.database import get_connection

router = APIRouter(prefix="/study", tags=["study"])


@router.post("/start")
def start_study(
    current_user_id: int = Depends(get_current_user_id),
):
    conn = None
    try:
        conn = get_connection()

        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id, nickname FROM users WHERE id = %s",
                (current_user_id,)
            )
            user = cursor.fetchone()

            if not user:
                raise HTTPException(status_code=404, detail="존재하지 않는 user_id입니다.")

            cursor.execute(
                """
                SELECT id
                FROM study_sessions
                WHERE user_id = %s AND ended_at IS NULL
                ORDER BY started_at DESC
                LIMIT 1
                """,
                (current_user_id,)
            )
            active_session = cursor.fetchone()

            if active_session:
                raise HTTPException(status_code=400, detail="이미 공부 중인 세션이 존재합니다.")

            kst = ZoneInfo("Asia/Seoul")
            now = datetime.now(kst)

            cursor.execute(
                """
                INSERT INTO study_sessions (user_id, started_at)
                VALUES (%s, %s)
                """,
                (current_user_id, now)
            )

            session_id = cursor.lastrowid

            cursor.execute(
                """
                SELECT id, user_id, started_at, ended_at, duration_seconds
                FROM study_sessions
                WHERE id = %s
                """,
                (session_id,)
            )
            session = cursor.fetchone()

        return {
            "message": "공부 시작 기록이 저장되었습니다.",
            "session": session
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"서버 오류: {str(e)}")
    finally:
        if conn:
            conn.close()


@router.post("/stop")
def stop_study(
    current_user_id: int = Depends(get_current_user_id),
):
    conn = None
    try:
        conn = get_connection()

        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id, nickname FROM users WHERE id = %s",
                (current_user_id,)
            )
            user = cursor.fetchone()

            if not user:
                raise HTTPException(status_code=404, detail="존재하지 않는 user_id입니다.")

            cursor.execute(
                """
                SELECT id, user_id, started_at, ended_at, duration_seconds
                FROM study_sessions
                WHERE user_id = %s AND ended_at IS NULL
                ORDER BY started_at DESC
                LIMIT 1
                """,
                (current_user_id,)
            )
            active_session = cursor.fetchone()

            if not active_session:
                raise HTTPException(status_code=400, detail="현재 종료할 공부 세션이 없습니다.")

            kst = ZoneInfo("Asia/Seoul")
            now = datetime.now(kst)
            started_at = active_session["started_at"]
            if started_at.tzinfo is None:
                started_at = started_at.replace(tzinfo=kst)
            duration_seconds = int((now - started_at).total_seconds())

            if duration_seconds < 0:
                raise HTTPException(status_code=400, detail="비정상적인 시간 계산이 발생했습니다.")

            cursor.execute(
                """
                UPDATE study_sessions
                SET ended_at = %s,
                    duration_seconds = %s
                WHERE id = %s
                """,
                (now, duration_seconds, active_session["id"])
            )

            cursor.execute(
                """
                SELECT id, user_id, started_at, ended_at, duration_seconds
                FROM study_sessions
                WHERE id = %s
                """,
                (active_session["id"],)
            )
            updated_session = cursor.fetchone()

        return {
            "message": "공부 종료 기록이 저장되었습니다.",
            "session": updated_session
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"서버 오류: {str(e)}")
    finally:
        if conn:
            conn.close()
