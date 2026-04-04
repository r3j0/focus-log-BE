import re
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Response

from app.auth_utils import (
    AuthTokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.database import get_connection
from app.schemas import (
    AuthCredentialRequest,
    AuthTokenResponse,
    RefreshTokenResponse,
    TokenRefreshRequest,
)

router = APIRouter(prefix="/auth", tags=["auth"])

NICKNAME_PATTERN = re.compile(r"^[A-Za-z0-9가-힣_]{2,20}$")
PASSWORD_PATTERN = re.compile(r"^(?=.*[A-Za-z])(?=.*\d).{8,64}$")


def _validate_credential_input(request: AuthCredentialRequest) -> tuple[str, str]:
    nickname = request.nickname.strip()
    password = request.password

    if not NICKNAME_PATTERN.match(nickname):
        raise HTTPException(
            status_code=400,
            detail="nickname은 2~20자, 한글/영문/숫자/밑줄(_)만 사용할 수 있습니다.",
        )

    if not PASSWORD_PATTERN.match(password):
        raise HTTPException(
            status_code=400,
            detail="password는 8~64자이며 영문과 숫자를 최소 1자 이상 포함해야 합니다.",
        )

    return nickname, password


def _issue_token_pair(cursor, user_id: int) -> tuple[str, int, str]:
    access_token, access_expires_in = create_access_token(user_id)
    refresh_token, refresh_expires_at = create_refresh_token(user_id)

    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)

    cursor.execute(
        """
        INSERT INTO refresh_tokens (user_id, token_hash, expires_at, created_at)
        VALUES (%s, %s, %s, %s)
        """,
        (
            user_id,
            hash_refresh_token(refresh_token),
            refresh_expires_at.replace(tzinfo=None),
            now_utc,
        ),
    )

    return access_token, access_expires_in, refresh_token


@router.post("/signup", response_model=AuthTokenResponse)
def signup(request: AuthCredentialRequest):
    conn = None
    try:
        nickname, password = _validate_credential_input(request)
        conn = get_connection()

        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id FROM users WHERE nickname = %s LIMIT 1",
                (nickname,),
            )
            existing_user = cursor.fetchone()
            if existing_user:
                raise HTTPException(status_code=409, detail="이미 사용 중인 nickname입니다.")

            cursor.execute(
                """
                INSERT INTO users (nickname, password_hash)
                VALUES (%s, %s)
                """,
                (nickname, hash_password(password)),
            )
            user_id = int(cursor.lastrowid)

            access_token, access_expires_in, refresh_token = _issue_token_pair(cursor, user_id)

        return {
            "user_id": user_id,
            "nickname": nickname,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "access_expires_in": access_expires_in,
        }
    except HTTPException:
        raise
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=f"인증 설정 오류: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"서버 오류: {str(e)}")
    finally:
        if conn:
            conn.close()


@router.post("/login", response_model=AuthTokenResponse)
def login(request: AuthCredentialRequest):
    conn = None
    try:
        nickname, password = _validate_credential_input(request)
        conn = get_connection()

        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, nickname, password_hash
                FROM users
                WHERE nickname = %s
                LIMIT 1
                """,
                (nickname,),
            )
            user = cursor.fetchone()

            if not user or not verify_password(password, user.get("password_hash")):
                raise HTTPException(status_code=401, detail="닉네임 또는 비밀번호가 올바르지 않습니다.")

            user_id = int(user["id"])
            access_token, access_expires_in, refresh_token = _issue_token_pair(cursor, user_id)

        return {
            "user_id": user_id,
            "nickname": user["nickname"],
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "access_expires_in": access_expires_in,
        }
    except HTTPException:
        raise
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=f"인증 설정 오류: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"서버 오류: {str(e)}")
    finally:
        if conn:
            conn.close()


@router.post("/refresh", response_model=RefreshTokenResponse)
def refresh_token(request: TokenRefreshRequest):
    conn = None
    try:
        raw_refresh_token = request.refresh_token.strip()
        if not raw_refresh_token:
            raise HTTPException(status_code=400, detail="refresh_token이 필요합니다.")

        payload = decode_token(raw_refresh_token, expected_type="refresh")
        try:
            user_id = int(payload["sub"])
        except (TypeError, ValueError):
            raise HTTPException(status_code=401, detail="토큰의 사용자 정보가 올바르지 않습니다.")
        token_hash = hash_refresh_token(raw_refresh_token)

        conn = get_connection()
        now_utc = datetime.now(timezone.utc).replace(tzinfo=None)

        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, user_id, expires_at, revoked_at
                FROM refresh_tokens
                WHERE token_hash = %s
                LIMIT 1
                """,
                (token_hash,),
            )
            token_row = cursor.fetchone()

            if not token_row:
                raise HTTPException(status_code=401, detail="유효하지 않은 refresh token입니다.")

            if int(token_row["user_id"]) != user_id:
                raise HTTPException(status_code=401, detail="토큰 사용자 정보가 일치하지 않습니다.")

            if token_row["revoked_at"] is not None:
                raise HTTPException(status_code=401, detail="이미 폐기된 refresh token입니다.")

            expires_at = token_row["expires_at"]
            if expires_at.tzinfo is not None:
                expires_at = expires_at.astimezone(timezone.utc).replace(tzinfo=None)

            if expires_at <= now_utc:
                raise HTTPException(status_code=401, detail="만료된 refresh token입니다.")

            cursor.execute(
                """
                UPDATE refresh_tokens
                SET revoked_at = %s
                WHERE id = %s
                  AND revoked_at IS NULL
                """,
                (now_utc, token_row["id"]),
            )
            if cursor.rowcount == 0:
                raise HTTPException(status_code=401, detail="이미 폐기된 refresh token입니다.")

            access_token, access_expires_in, new_refresh_token = _issue_token_pair(cursor, user_id)

        return {
            "access_token": access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
            "access_expires_in": access_expires_in,
        }
    except HTTPException:
        raise
    except AuthTokenError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=f"인증 설정 오류: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"서버 오류: {str(e)}")
    finally:
        if conn:
            conn.close()


@router.post("/logout", status_code=204)
def logout(request: TokenRefreshRequest):
    conn = None
    try:
        raw_refresh_token = request.refresh_token.strip()
        if not raw_refresh_token:
            raise HTTPException(status_code=400, detail="refresh_token이 필요합니다.")

        decode_token(raw_refresh_token, expected_type="refresh")
        token_hash = hash_refresh_token(raw_refresh_token)

        conn = get_connection()
        now_utc = datetime.now(timezone.utc).replace(tzinfo=None)

        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE refresh_tokens
                SET revoked_at = %s
                WHERE token_hash = %s
                  AND revoked_at IS NULL
                """,
                (now_utc, token_hash),
            )

            if cursor.rowcount == 0:
                raise HTTPException(status_code=401, detail="유효하지 않거나 이미 폐기된 refresh token입니다.")

        return Response(status_code=204)
    except HTTPException:
        raise
    except AuthTokenError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=f"인증 설정 오류: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"서버 오류: {str(e)}")
    finally:
        if conn:
            conn.close()
