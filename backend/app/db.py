"""Database tables and connection helpers (SQLModel on top of SQLAlchemy).

Tables:
- User:         an account (email + hashed password).
- Profile:      one per user; everything an application form might ask, filled in once.
- SavedAnswer:  answers to extra form questions, reused on later applications.
- Resume:       an uploaded resume: the original file, its text, and the parsed profile.
- Application:  one job you analysed, its tracker status, and the `thread_id`
                that links it to the agent's saved state in the LangGraph checkpointer.

Every table except User has a `user_id`, and every query filters by it, so one
user can never see another user's data.

The schema is created and changed by Alembic migrations (see `migrations/`),
never by `create_all`, so production databases can be upgraded safely.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

from sqlalchemy import JSON, Column, LargeBinary, UniqueConstraint
from sqlmodel import Field, Session, SQLModel, create_engine

from app.config import get_settings

BACKEND_DIR = Path(__file__).resolve().parent.parent


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


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    # Always stored lower-case, so "Me@Gmail.com" and "me@gmail.com" are the same account.
    email: str = Field(index=True, unique=True, max_length=320)
    password_hash: str
    created_at: datetime = Field(default_factory=_now)


class Profile(SQLModel, table=True):
    user_id: int = Field(foreign_key="user.id", primary_key=True)
    # The ProfileData model (app/profile_schema.py) stored as JSON. One JSON column
    # instead of ~40 columns: new fields don't need a database migration, and the
    # Pydantic model validates every save.
    data: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    # The resume used for new applications and uploaded to job forms.
    active_resume_id: int | None = Field(default=None, foreign_key="resume.id")
    updated_at: datetime = Field(default_factory=_now)


class SavedAnswer(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("user_id", "question_key"),)

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    question: str = Field(max_length=500)
    # Normalised question text, so "Notice period?" and "notice period" match.
    question_key: str = Field(max_length=500)
    answer: str = Field(max_length=5000)
    # "manual" if you typed it on the profile page, "application" if saved while applying.
    source: str = "manual"
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


class Resume(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    label: str = "My resume"
    raw_text: str
    profile: dict[str, Any] = Field(sa_column=Column(JSON))
    # The original file, kept so it can be attached to job applications later.
    # Stored in the database because free hosting wipes local files.
    file_name: str = ""
    content_type: str = ""
    file_data: bytes | None = Field(default=None, sa_column=Column(LargeBinary, nullable=True))
    created_at: datetime = Field(default_factory=_now)


class Application(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
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
        s = get_settings()
        if s.is_postgres:
            # pool_pre_ping: free hosted Postgres (e.g. Neon) suspends idle databases,
            # which drops open connections; check each one before use.
            _engine = create_engine(s.sqlalchemy_url, pool_pre_ping=True, pool_size=5, max_overflow=5)
        else:
            Path(s.database_url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
            _engine = create_engine(s.database_url, connect_args={"check_same_thread": False})
    return _engine


def run_migrations() -> None:
    """Bring the database schema up to date (`alembic upgrade head`)."""
    from alembic import command
    from alembic.config import Config

    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    cfg.attributes["configure_logger"] = False  # keep the API's own logging setup
    command.upgrade(cfg, "head")


def get_session() -> Iterator[Session]:
    with Session(get_engine()) as session:
        yield session


def reset_engine() -> None:
    """Testing helper."""
    global _engine
    if _engine is not None:
        _engine.dispose()
    _engine = None
