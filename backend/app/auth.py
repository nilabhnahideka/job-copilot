"""Accounts: password hashing, login tokens, and the "who is logged in" dependency.

How login works:
1. Sign up / log in with email + password. Passwords are never stored, only an
   Argon2 hash of them (a one-way scramble that can be checked but not reversed).
2. The API returns a signed token (a JWT) that says "this is user 42, valid for 7 days".
3. The website sends it with every request in the `Authorization: Bearer <token>` header.
4. `get_current_user` checks the signature and expiry, then loads the user.
   No valid token = 401 Unauthorized.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pwdlib import PasswordHash
from sqlmodel import Session

from app.config import get_settings
from app.db import User, get_session

ALGORITHM = "HS256"

# Argon2id with the library's recommended settings.
_hasher = PasswordHash.recommended()
# Hash of a random string, used to keep failed logins for unknown emails as slow
# as failed logins for real ones (so timing doesn't reveal which emails exist).
_DUMMY_HASH = _hasher.hash("not-a-real-password-just-for-timing")

_bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    if password_hash is None:
        _hasher.verify(password, _DUMMY_HASH)
        return False
    return _hasher.verify(password, password_hash)


def normalise_email(email: str) -> str:
    return email.strip().lower()


def create_access_token(user_id: int) -> str:
    s = get_settings()
    now = datetime.now(UTC)
    payload = {"sub": str(user_id), "iat": now, "exp": now + timedelta(days=s.jwt_expire_days)}
    return jwt.encode(payload, s.jwt_secret, algorithm=ALGORITHM)


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(status.HTTP_401_UNAUTHORIZED, detail, headers={"WWW-Authenticate": "Bearer"})


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: Session = Depends(get_session),
) -> User:
    if creds is None:
        raise _unauthorized("Log in to continue")
    try:
        payload = jwt.decode(creds.credentials, get_settings().jwt_secret, algorithms=[ALGORITHM])
        user_id = int(payload["sub"])
    except jwt.ExpiredSignatureError as e:
        raise _unauthorized("Your session expired. Log in again.") from e
    except (jwt.InvalidTokenError, KeyError, ValueError) as e:
        raise _unauthorized("Invalid login token. Log in again.") from e

    user = session.get(User, user_id)
    if user is None:  # account was deleted after the token was issued
        raise _unauthorized("Account not found. Log in again.")
    return user
