"""Database tables and connection helpers (SQLModel on top of SQLAlchemy).

Two tables:
- Resume: the raw resume text plus its parsed, structured profile.
- Application: one job you analysed, its tracker status, and the `thread_id`
  that links it to the agent's saved state in the LangGraph checkpointer."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

from sqlalchemy import JSON, Column
from sqlmodel import Field, Session, SQLModel, create_engine

from app.config import get_settings


def _now() -> datetime:
    return datetime.now(UTC)


class ApplicationStatus(str, Enum):
    draft = "draft"  # agent ran, awaiting your review
    ready = "ready"  # drafts approved
    applied = "applied"
    interviewing = "interviewing"
    offer = "offer"
    rejected = "rejected"
    archived = "archived"


class Resume(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    label: str = "My resume"
    raw_text: str
    profile: dict[str, Any] = Field(sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=_now)


class Application(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    resume_id: int = Field(foreign_key="resume.id")
    thread_id: str = Field(index=True, unique=True)

    company: str = ""
    title: str = ""
    job_url: str = ""
    job_text: str

    status: ApplicationStatus = ApplicationStatus.draft
    fit_score: int | None = None
    notes: str = ""

    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


_engine = None


def get_engine():
    global _engine
    if _engine is None:
        url = get_settings().database_url
        if url.startswith("sqlite:///"):
            Path(url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
            _engine = create_engine(url, connect_args={"check_same_thread": False})
        else:
            _engine = create_engine(url, pool_pre_ping=True)
    return _engine


def init_db() -> None:
    SQLModel.metadata.create_all(get_engine())


def get_session() -> Iterator[Session]:
    with Session(get_engine()) as session:
        yield session


def reset_engine() -> None:
    """Testing helper."""
    global _engine
    _engine = None
