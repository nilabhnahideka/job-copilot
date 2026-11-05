"""Sign up, log in, and "who am I".

POST /api/auth/signup   create an account, returns a login token
POST /api/auth/login    exchange email + password for a login token
GET  /api/auth/me       the logged-in user
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.auth import (
    create_access_token,
    get_current_user,
    hash_password,
    normalise_email,
    verify_password,
)
from app.db import User, get_session
from app.profile_service import get_or_create_profile

router = APIRouter(prefix="/api/auth", tags=["auth"])


class Credentials(BaseModel):
    email: EmailStr
    # 8 minimum for safety; 128 maximum so nobody can send a huge string to slow hashing down.
    password: str = Field(min_length=8, max_length=128)


class LoginBody(BaseModel):
    # No length rules here: a wrong password should get "incorrect", not a validation error.
    email: EmailStr
    password: str = Field(max_length=128)


class UserOut(BaseModel):
    id: int
    email: str
    created_at: datetime


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


def _token_response(user: User) -> TokenOut:
    return TokenOut(
        access_token=create_access_token(user.id),
        user=UserOut(id=user.id, email=user.email, created_at=user.created_at),
    )


@router.post("/signup", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def signup(body: Credentials, session: Session = Depends(get_session)):
    email = normalise_email(body.email)
    if session.exec(select(User).where(User.email == email)).first():
        raise HTTPException(
            status.HTTP_409_CONFLICT, "An account with this email already exists. Log in instead."
        )

    user = User(email=email, password_hash=hash_password(body.password))
    session.add(user)
    try:
        session.commit()
    except IntegrityError as e:  # two sign-ups with the same email at the same moment
        session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists.") from e
    session.refresh(user)

    # Start the profile with the email they signed up with.
    profile = get_or_create_profile(session, user.id)
    profile.data = {**profile.data, "personal": {**profile.data.get("personal", {}), "email": email}}
    session.add(profile)
    session.commit()
    return _token_response(user)


@router.post("/login", response_model=TokenOut)
def login(body: LoginBody, session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.email == normalise_email(body.email))).first()
    # Same message whether the email or the password is wrong, so the login form
    # can't be used to find out which emails have accounts.
    if not verify_password(body.password, user.password_hash if user else None):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Email or password is incorrect")
    return _token_response(user)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return UserOut(id=user.id, email=user.email, created_at=user.created_at)
