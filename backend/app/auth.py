"""Authentication helpers — password hashing, JWT token management, and
FastAPI dependency for extracting the authenticated user from a request.

Tokens
------
- **Access token** (short-lived, 24 h) — attached as ``Authorization: Bearer …``
  to every API call.
- **Refresh token** (long-lived, 30 d) — used once to obtain a new access token
  when the old one expires, without forcing re-login.
"""

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import HTTPException, Request

from . import config

# ---------------------------------------------------------------------------
# Password hashing (bcrypt)
# ---------------------------------------------------------------------------



def hash_password(plain: str) -> str:
    """Return a bcrypt hash of *plain*."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(plain.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Check *plain* against a stored bcrypt *hashed* value."""
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------

def create_access_token(user_id: int) -> str:
    """Create a short-lived access token embedding the *user_id*."""
    payload = {
        "sub": str(user_id),
        "type": "access",
        "exp": datetime.now(timezone.utc)
              + timedelta(hours=config.JWT_ACCESS_TOKEN_EXPIRE_HOURS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, config.JWT_SECRET_KEY,
                      algorithm=config.JWT_ALGORITHM)


def create_refresh_token(user_id: int) -> str:
    """Create a long-lived refresh token embedding the *user_id*."""
    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "exp": datetime.now(timezone.utc)
              + timedelta(days=config.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, config.JWT_SECRET_KEY,
                      algorithm=config.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and validate a JWT, returning the payload dict.

    Raises ``HTTPException(401)`` on any failure (expired, tampered, etc.).
    """
    try:
        return jwt.decode(token, config.JWT_SECRET_KEY,
                          algorithms=[config.JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token süresi dolmuş — lütfen tekrar giriş yapın")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Geçersiz token")


# ---------------------------------------------------------------------------
# FastAPI dependency — extracts user_id from the Bearer token
# ---------------------------------------------------------------------------

def _extract_bearer(request: Request) -> str:
    """Pull the token string from the ``Authorization`` header."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(401, "Yetkilendirme başlığı eksik")
    return auth[7:]


def get_current_user_id(request: Request) -> int:
    """FastAPI dependency: returns the authenticated *user_id*.

    Usage::

        @app.get("/protected")
        def protected(uid: int = Depends(get_current_user_id)):
            ...
    """
    token = _extract_bearer(request)
    payload = decode_token(token)
    if payload.get("type") != "access":
        raise HTTPException(401, "Erişim token'ı bekleniyor (access token)")
    try:
        return int(payload["sub"])
    except (KeyError, ValueError):
        raise HTTPException(401, "Token geçersiz — kullanıcı kimliği bulunamadı")


def require_same_user(token_user_id: int, requested_user_id: int) -> None:
    """Raise 403 if the token owner is not the user being accessed."""
    if token_user_id != requested_user_id:
        raise HTTPException(403, "Başka kullanıcının verisine erişim engellendi")

