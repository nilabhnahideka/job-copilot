"""Shared pytest fixtures: a fake LLM and an API test client on a temporary database."""

import pytest
from fastapi.testclient import TestClient

from app import db
from app.config import get_settings
from app.llm import set_llm
from tests.fakes import FakeLLM


@pytest.fixture
def fake_llm():
    llm = FakeLLM()
    set_llm(llm)
    yield llm
    set_llm(None)


@pytest.fixture
def client(tmp_path, monkeypatch, fake_llm):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/test.db")
    monkeypatch.setenv("CHECKPOINT_DB_PATH", str(tmp_path / "ckpt.db"))
    get_settings.cache_clear()
    db.reset_engine()
    from app.main import app

    with TestClient(app) as c:
        yield c
    get_settings.cache_clear()
    db.reset_engine()
