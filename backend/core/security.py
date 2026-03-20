"""密码与会话安全工具。"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import time

from fastapi import Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.core.database import get_db
from backend.core.models import User


PBKDF2_ITERATIONS = 390000


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PBKDF2_ITERATIONS,
    )
    encoded_digest = base64.b64encode(digest).decode("ascii")
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt}${encoded_digest}"


def is_hashed_password(password: str) -> bool:
    return password.startswith("pbkdf2_sha256$")


def verify_password(plain_password: str, stored_password: str) -> bool:
    if not stored_password:
        return False

    if not is_hashed_password(stored_password):
        return hmac.compare_digest(plain_password, stored_password)

    try:
        _, iterations, salt, encoded_digest = stored_password.split("$", 3)
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            plain_password.encode("utf-8"),
            salt.encode("utf-8"),
            int(iterations),
        )
        candidate = base64.b64encode(digest).decode("ascii")
        return hmac.compare_digest(candidate, encoded_digest)
    except (ValueError, TypeError):
        return False


def needs_password_upgrade(stored_password: str) -> bool:
    return not is_hashed_password(stored_password)


def create_session_token(user_id: int, expires_in: int | None = None) -> str:
    expires_at = int(time.time()) + (expires_in or settings.SESSION_MAX_AGE)
    payload = f"{user_id}:{expires_at}"
    signature = hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    token = f"{payload}:{signature}"
    return base64.urlsafe_b64encode(token.encode("utf-8")).decode("ascii")


def validate_session_token(token: str) -> int | None:
    try:
        decoded = base64.urlsafe_b64decode(token.encode("ascii")).decode("utf-8")
        user_id_text, expires_at_text, signature = decoded.split(":", 2)
        payload = f"{user_id_text}:{expires_at_text}"
        expected_signature = hmac.new(
            settings.SECRET_KEY.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(signature, expected_signature):
            return None
        if int(expires_at_text) < int(time.time()):
            return None

        return int(user_id_text)
    except (ValueError, TypeError, UnicodeDecodeError, base64.binascii.Error):
        return None


def set_session_cookie(response: Response, user_id: int) -> None:
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=create_session_token(user_id),
        max_age=settings.SESSION_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=False,
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.SESSION_COOKIE_NAME,
        httponly=True,
        samesite="lax",
        secure=False,
        path="/",
    )


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    user_id = validate_session_token(token) if token else None
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="请先登录",
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="登录状态已失效",
        )
    return user


def require_same_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权访问该用户资源",
        )
    return current_user
