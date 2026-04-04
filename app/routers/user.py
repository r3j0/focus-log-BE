from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo
from pydantic import BaseModel

from app.auth_utils import get_current_user_id
from app.database import get_connection

router = APIRouter(prefix="/user", tags=["user"])


class UserRecordRequestBody(BaseModel):
    date: str | None = None


@router.post("/record")
def user_record(
    request: UserRecordRequestBody,
    current_user_id: int = Depends(get_current_user_id),
):
    conn = None
    try:
        conn = get_connection()

        with conn.cursor() as cursor:
            # 1) user 존재 확인
            cursor.execute(
                "SELECT id, nickname FROM users WHERE id = %s",
                (current_user_id,)
            )
            user = cursor.fetchone()

            if not user:
                raise HTTPException(status_code=404, detail="존재하지 않는 user_id입니다.")

            # 2) 날짜 결정
            kst = ZoneInfo("Asia/Seoul")

            if request.date is None:
                selected_date = datetime.now(kst).date()
            else:
                try:
                    selected_date = date.fromisoformat(request.date)
                except ValueError:
                    raise HTTPException(
                        status_code=400,
                        detail="date는 YYYY-MM-DD 형식이어야 합니다."
                    )

            # 3) 해당 날짜 시작/끝 계산
            day_start = datetime.combine(selected_date, datetime.min.time(), tzinfo=kst)
            next_day_start = day_start + timedelta(days=1)

            # pymysql DATETIME 비교용 naive datetime
            day_start_naive = day_start.replace(tzinfo=None)
            next_day_start_naive = next_day_start.replace(tzinfo=None)

            # 4) 해당 날짜 세션 조회
            cursor.execute(
                """
                SELECT id, user_id, started_at, ended_at, duration_seconds
                FROM study_sessions
                WHERE user_id = %s
                  AND started_at >= %s
                  AND started_at < %s
                ORDER BY started_at DESC
                """,
                (current_user_id, day_start_naive, next_day_start_naive)
            )
            sessions = cursor.fetchall()

            # 5) 총 공부 시간 계산
            total_duration_seconds = sum(
                session["duration_seconds"] or 0 for session in sessions
            )

        return {
            "user_id": user["id"],
            "nickname": user["nickname"],
            "date": selected_date.isoformat(),
            "total_duration_seconds": total_duration_seconds,
            "sessions": sessions
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"서버 오류: {str(e)}")
    finally:
        if conn:
            conn.close()
