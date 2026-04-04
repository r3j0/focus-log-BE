import hashlib
import os
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from dotenv import load_dotenv

load_dotenv()

ALGORITHM = "HS256"
DEFAULT_ACCESS_SECRET = "dev-access-secret-change-this-to-env-value-1234567890"
DEFAULT_REFRESH_SECRET = "dev-refresh-secret-change-this-to-env-value-1234567890"


class AuthTokenError(Exception):
    pass


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _resolve_secret(primary_name: str, fallback_names: tuple[str, ...], default_value: str) -> str:
    names = (primary_name, *fallback_names)
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return default_value


def access_expire_minutes() -> int:
    return int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))


def refresh_expire_days() -> int:
    return int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "14"))


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str | None) -> bool:
    if not password_hash:
        return False

    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def hash_refresh_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def _issue_token(payload: dict, secret: str, expires_delta: timedelta) -> tuple[str, datetime]:
    now = _utc_now()
    expires_at = now + expires_delta

    encoded_payload = {
        **payload,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    token = jwt.encode(encoded_payload, secret, algorithm=ALGORITHM)
    return token, expires_at


def create_access_token(user_id: int) -> tuple[str, int]:
    minutes = access_expire_minutes()
    token, _ = _issue_token(
        payload={
            "sub": str(user_id),
            "type": "access",
            "jti": uuid.uuid4().hex,
        },
        secret=_resolve_secret(
            "JWT_ACCESS_SECRET",
            ("JWT_SECRET", "SECRET_KEY"),
            DEFAULT_ACCESS_SECRET,
        ),
        expires_delta=timedelta(minutes=minutes),
    )
    return token, minutes * 60


def create_refresh_token(user_id: int) -> tuple[str, datetime]:
    token, expires_at = _issue_token(
        payload={
            "sub": str(user_id),
            "type": "refresh",
            "jti": uuid.uuid4().hex,
        },
        secret=_resolve_secret(
            "JWT_REFRESH_SECRET",
            ("JWT_SECRET", "SECRET_KEY"),
            DEFAULT_REFRESH_SECRET,
        ),
        expires_delta=timedelta(days=refresh_expire_days()),
    )
    return token, expires_at


def decode_token(token: str, expected_type: str) -> dict:
    if expected_type == "access":
        secret = _resolve_secret(
            "JWT_ACCESS_SECRET",
            ("JWT_SECRET", "SECRET_KEY"),
            DEFAULT_ACCESS_SECRET,
        )
    else:
        secret = _resolve_secret(
            "JWT_REFRESH_SECRET",
            ("JWT_SECRET", "SECRET_KEY"),
            DEFAULT_REFRESH_SECRET,
        )

    try:
        payload = jwt.decode(token, secret, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise AuthTokenError("만료된 토큰입니다.") from exc
    except jwt.InvalidTokenError as exc:
        raise AuthTokenError("유효하지 않은 토큰입니다.") from exc

    token_type = payload.get("type")
    if token_type != expected_type:
        raise AuthTokenError("토큰 타입이 올바르지 않습니다.")

    sub = payload.get("sub")
    if sub is None:
        raise AuthTokenError("토큰의 사용자 정보가 없습니다.")

    return payload
