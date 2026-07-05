"""
Auth: password hashing + JWT
==============================
- Password kabhi plaintext store nahi hota — bcrypt hash (passlib) store hota hai.
- Login ke baad ek JWT access token milta hai jo 24 hours (JWT_EXPIRY_SECONDS)
  ke liye valid hota hai. Har protected API call is token ko
  `Authorization: Bearer <token>` header me expect karti hai.

JWT expiry ka matlab: token ke andar hi ek "exp" (expiry unix-timestamp) likha
hota hai. Us waqt ke baad token invalid ho jata hai, user ko dobara /auth/login
call karke naya token lena padta hai.
"""

from __future__ import annotations

import os
import time

from passlib.context import CryptContext
from jose import jwt, JWTError

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

JWT_ALGORITHM = "HS256"
JWT_EXPIRY_SECONDS = 24 * 60 * 60  # 24 hours — confirmed with user


class AuthError(Exception):
    pass


def _get_jwt_secret() -> str:
    secret = os.getenv("JWT_SECRET_KEY")
    if not secret:
        raise AuthError(
            "JWT_SECRET_KEY missing hai .env me. Generate karo:\n"
            "  python -c \"import secrets; print(secrets.token_urlsafe(48))\""
        )
    return secret


# ---------------- Password hashing ----------------
def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return pwd_context.verify(password, password_hash)
    except Exception:
        return False


# ---------------- JWT ----------------
def create_access_token(username: str) -> dict:
    secret = _get_jwt_secret()
    now = int(time.time())
    payload = {"sub": username, "iat": now, "exp": now + JWT_EXPIRY_SECONDS}
    token = jwt.encode(payload, secret, algorithm=JWT_ALGORITHM)
    return {"access_token": token, "token_type": "bearer", "expires_in": JWT_EXPIRY_SECONDS}


def decode_access_token(token: str) -> str:
    """Returns username (the 'sub' claim). Raises AuthError if invalid/expired."""
    secret = _get_jwt_secret()
    try:
        payload = jwt.decode(token, secret, algorithms=[JWT_ALGORITHM])
    except JWTError as e:
        raise AuthError(f"Invalid or expired token: {e}")
    username = payload.get("sub")
    if not username:
        raise AuthError("Token missing subject")
    return username


# ---------------- Account storage (username/password) ----------------
ACCOUNT_KEY = "account"


async def user_exists(store, username: str) -> bool:
    item = await store.aget(namespace=("users", username), key=ACCOUNT_KEY)
    return item is not None


async def create_user_account(store, username: str, password: str) -> None:
    if await user_exists(store, username):
        raise ValueError("Username already exists")
    await store.aput(
        namespace=("users", username),
        key=ACCOUNT_KEY,
        value={"password_hash": hash_password(password), "created_at": time.time()},
    )


async def verify_login(store, username: str, password: str) -> bool:
    item = await store.aget(namespace=("users", username), key=ACCOUNT_KEY)
    if not item:
        return False
    return verify_password(password, item.value.get("password_hash", ""))