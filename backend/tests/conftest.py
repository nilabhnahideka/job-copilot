"""Shared pytest fixtures: a fake LLM and an API test client on a fresh, empty database.

By default each test gets its own temporary SQLite database. To run the same tests
against Postgres (as CI does), point TEST_DATABASE_URL at an empty test database:

    TEST_DATABASE_URL=postgresql://postgres@localhost:5432/copilot_test pytest

WARNING: the tests wipe that database before every test.
"""

import os

import pytest
from fastapi.testclient import TestClient

from app import db
from app.config import get_settings
from app.llm import set_llm
from tests.fakes import FakeLLM

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")


def _wipe_postgres(url: str) -> None:
    import psycopg

    with psycopg.connect(url.replace("postgresql+psycopg://", "postgresql://"), autocommit=True) as conn:
        conn.execute("DROP SCHEMA public CASCADE")
        conn.execute("CREATE SCHEMA public")


@pytest.fixture
def fake_llm():
    llm = FakeLLM()
    set_llm(llm)
    yield llm
    set_llm(None)


@pytest.fixture
def client(tmp_path, monkeypatch, fake_llm):
    if TEST_DATABASE_URL:
        _wipe_postgres(TEST_DATABASE_URL)
        monkeypatch.setenv("DATABASE_URL", TEST_DATABASE_URL)
    else:
        monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/test.db")
        monkeypatch.setenv("CHECKPOINT_DB_PATH", str(tmp_path / "ckpt.db"))
    get_settings.cache_clear()
    db.reset_engine()
    from app.main import app

    with TestClient(app) as c:  # runs startup: migrations + checkpointer
        yield c
    get_settings.cache_clear()
    db.reset_engine()


@pytest.fixture
def signup(client):
    """Create an account and return the auth headers for it: `headers = signup("a@x.com")`."""

    def _signup(email: str = "asha@example.com", password: str = "correct-horse-1") -> dict:
        r = client.post("/api/auth/signup", json={"email": email, "password": password})
        assert r.status_code == 201, r.text
        return {"Authorization": f"Bearer {r.json()['access_token']}"}

    return _signup


@pytest.fixture
def auth(signup):
    """Auth headers for a default test user."""
    return signup()
