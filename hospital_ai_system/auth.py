from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import Cookie, HTTPException, status
from passlib.context import CryptContext

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-change-me")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "120"))

COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"
COOKIE_SAMESITE = os.getenv("COOKIE_SAMESITE", "lax").lower()

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

COOKIE_NAME = "access_token"


def hash_password(password: str) -> str:
    return pwd_context.hash(password or "")


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password or "", password_hash)


def create_access_token(*, sub: str, role: str, expires_delta: Optional[timedelta] = None) -> str:
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta if expires_delta else timedelta(minutes=JWT_EXPIRE_MINUTES))
    payload = {"sub": sub, "role": role, "iat": int(now.timestamp()), "exp": int(expire.timestamp())}
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired") from e
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from e


def get_token_from_cookie(access_token: Optional[str] = Cookie(default=None, alias=COOKIE_NAME)) -> str:
    if not access_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return access_token