"""Tests for sign up, log in, and login tokens."""

from datetime import UTC, datetime, timedelta

import jwt

from app.config import get_settings


def test_signup_returns_token_and_starts_profile_with_email(client):
    r = client.post("/api/auth/signup", json={"email": "  Asha@Example.COM ", "password": "longenough1"})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["user"]["email"] == "asha@example.com"  # stored lower-case and trimmed
    headers = {"Authorization": f"Bearer {body['access_token']}"}

    assert client.get("/api/auth/me", headers=headers).json()["email"] == "asha@example.com"
    profile = client.get("/api/profile", headers=headers).json()
    assert profile["data"]["personal"]["email"] == "asha@example.com"


def test_duplicate_email_is_rejected_case_insensitively(client, signup):
    signup("asha@example.com")
    r = client.post("/api/auth/signup", json={"email": "ASHA@example.com", "password": "longenough1"})
    assert r.status_code == 409


def test_signup_validation(client):
    assert client.post("/api/auth/signup", json={"email": "a@b.com", "password": "short"}).status_code == 422
    assert (
        client.post("/api/auth/signup", json={"email": "not-an-email", "password": "longenough1"}).status_code
        == 422
    )


def test_login(client, signup):
    signup("asha@example.com", "correct-horse-1")
    ok = client.post("/api/auth/login", json={"email": "Asha@example.com", "password": "correct-horse-1"})
    assert ok.status_code == 200 and ok.json()["access_token"]

    wrong_pw = client.post("/api/auth/login", json={"email": "asha@example.com", "password": "nope"})
    unknown = client.post("/api/auth/login", json={"email": "who@example.com", "password": "correct-horse-1"})
    # Same status and message, so the form can't reveal which emails exist.
    assert wrong_pw.status_code == unknown.status_code == 401
    assert wrong_pw.json() == unknown.json()


def test_password_is_not_stored_in_plain_text(client, signup):
    from sqlmodel import Session, select

    from app.db import User, get_engine

    signup("asha@example.com", "correct-horse-1")
    with Session(get_engine()) as s:
        user = s.exec(select(User)).one()
    assert "correct-horse-1" not in user.password_hash
    assert user.password_hash.startswith("$argon2id$")


def test_protected_endpoints_need_a_valid_token(client):
    assert client.get("/api/profile").status_code == 401
    assert client.get("/api/applications").status_code == 401
    bad = {"Authorization": "Bearer not.a.real.token"}
    assert client.get("/api/auth/me", headers=bad).status_code == 401


def test_expired_and_forged_tokens_are_rejected(client, signup):
    signup()
    s = get_settings()
    past = datetime.now(UTC) - timedelta(days=1)
    expired = jwt.encode({"sub": "1", "iat": past, "exp": past}, s.jwt_secret, algorithm="HS256")
    forged = jwt.encode(
        {"sub": "1", "exp": datetime.now(UTC) + timedelta(days=1)}, "x" * 40, algorithm="HS256"
    )

    r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {expired}"})
    assert r.status_code == 401 and "expired" in r.json()["detail"]
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {forged}"}).status_code == 401


def test_production_refuses_unsafe_settings(monkeypatch):
    import pytest

    from app.config import Settings

    for var in ("JWT_SECRET", "OPENAI_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    # _env_file=None: ignore any real .env on this computer
    unsafe = Settings(_env_file=None, environment="production", database_url="sqlite:///x.db")
    with pytest.raises(RuntimeError) as e:
        unsafe.validate_for_production()
    assert "JWT_SECRET" in str(e.value) and "Postgres" in str(e.value)

    safe = Settings(
        _env_file=None,
        environment="production",
        database_url="postgresql://u:p@host/db",
        jwt_secret="r" * 48,
        openai_api_key="sk-test",
    )
    safe.validate_for_production()  # no error


def test_blank_jwt_secret_falls_back_to_dev_secret_and_is_refused_in_production():
    import pytest

    from app.config import DEV_JWT_SECRET, Settings

    s = Settings(_env_file=None, jwt_secret="  ")
    assert s.jwt_secret == DEV_JWT_SECRET
    prod = Settings(
        _env_file=None,
        environment="production",
        jwt_secret="",
        database_url="postgresql://u:p@h/d",
        openai_api_key="k",
    )
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        prod.validate_for_production()
