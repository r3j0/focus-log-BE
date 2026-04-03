from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from fastapi import APIRouter, HTTPException, Query

from app.database import get_connection
from app.schemas import RankRange, RankResponse

router = APIRouter(prefix="/rank", tags=["rank"])


def get_period_bounds(selected_range: RankRange) -> tuple[datetime, datetime]:
    kst = ZoneInfo("Asia/Seoul")
    today = datetime.now(kst).date()

    if selected_range == "today":
        period_start = datetime.combine(today, datetime.min.time(), tzinfo=kst)
        period_end = period_start + timedelta(days=1)
    elif selected_range == "week":
        week_start_date = today - timedelta(days=today.weekday())
        period_start = datetime.combine(week_start_date, datetime.min.time(), tzinfo=kst)
        period_end = period_start + timedelta(days=7)
    else:
        month_start_date = today.replace(day=1)
        period_start = datetime.combine(month_start_date, datetime.min.time(), tzinfo=kst)

        if month_start_date.month == 12:
            next_month_start_date = month_start_date.replace(
                year=month_start_date.year + 1, month=1
            )
        else:
            next_month_start_date = month_start_date.replace(
                month=month_start_date.month + 1
            )

        period_end = datetime.combine(next_month_start_date, datetime.min.time(), tzinfo=kst)

    # /user 라우터와 동일하게 DB DATETIME 비교를 위해 naive datetime으로 변환
    return period_start.replace(tzinfo=None), period_end.replace(tzinfo=None)


@router.get("", response_model=RankResponse)
def get_rank(
    range: RankRange = Query(
        ...,
        description="조회 기간 (today/week/month)",
    ),
):
    conn = None
    try:
        conn = get_connection()
        kst = ZoneInfo("Asia/Seoul")
        now_naive = datetime.now(kst).replace(tzinfo=None)
        period_start, period_end = get_period_bounds(range)

        users_by_id: dict[int, dict[str, int | str | bool]] = {}

        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    u.id AS user_id,
                    u.nickname,
                    SUM(s.duration_seconds) AS total_duration_seconds
                FROM study_sessions s
                JOIN users u ON u.id = s.user_id
                WHERE s.started_at >= %s
                  AND s.started_at < %s
                  AND s.duration_seconds IS NOT NULL
                GROUP BY u.id, u.nickname
                """,
                (period_start, period_end),
            )
            closed_rows = cursor.fetchall()

            for row in closed_rows:
                user_id = row["user_id"]
                users_by_id[user_id] = {
                    "user_id": user_id,
                    "nickname": row["nickname"],
                    "total_duration_seconds": int(row["total_duration_seconds"] or 0),
                    "is_studying": False,
                }

            cursor.execute(
                """
                SELECT
                    u.id AS user_id,
                    u.nickname,
                    s.started_at
                FROM study_sessions s
                JOIN users u ON u.id = s.user_id
                WHERE s.ended_at IS NULL
                """
            )
            active_rows = cursor.fetchall()

        for row in active_rows:
            user_id = row["user_id"]
            started_at = row["started_at"]

            if started_at.tzinfo is not None:
                started_at = started_at.astimezone(kst).replace(tzinfo=None)

            user_data = users_by_id.setdefault(
                user_id,
                {
                    "user_id": user_id,
                    "nickname": row["nickname"],
                    "total_duration_seconds": 0,
                    "is_studying": False,
                },
            )

            effective_start = max(started_at, period_start)
            active_seconds = max(0, int((now_naive - effective_start).total_seconds()))
            user_data["total_duration_seconds"] = int(user_data["total_duration_seconds"]) + active_seconds
            user_data["is_studying"] = True

        sorted_users = sorted(
            users_by_id.values(),
            key=lambda user: (-int(user["total_duration_seconds"]), int(user["user_id"])),
        )

        ranks = []
        previous_total: int | None = None
        current_rank = 0

        for index, user in enumerate(sorted_users, start=1):
            total_duration_seconds = int(user["total_duration_seconds"])

            if previous_total is None or total_duration_seconds != previous_total:
                current_rank = index
                previous_total = total_duration_seconds

            ranks.append(
                {
                    "rank": current_rank,
                    "user_id": user["user_id"],
                    "nickname": user["nickname"],
                    "total_duration_seconds": total_duration_seconds,
                    "is_studying": user["is_studying"],
                }
            )

        return {
            "range": range,
            "ranks": ranks,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"서버 오류: {str(e)}")
    finally:
        if conn:
            conn.close()
