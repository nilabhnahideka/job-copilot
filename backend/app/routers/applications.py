"""Job applications: run the agent on a job post, review its drafts, track progress.

POST   /api/applications              run the agent; it pauses for your review
POST   /api/applications/stream       same, streaming one progress event per agent step (SSE)
POST   /api/applications/{id}/review  revise one draft, or approve them
GET    /api/applications[?status=]    your applications (the tracker board)
GET    /api/applications/{id}         one application, with the agent's results
PATCH  /api/applications/{id}         change status / notes / company / title
DELETE /api/applications/{id}         delete it and the agent's saved state

Every endpoint only sees the logged-in user's applications. Someone else's id
returns 404, the same as an id that doesn't exist, so ids can't be probed.

The agent's results are not copied into this table: they live in the
checkpointer, keyed by the application's `thread_id`, and are read from there.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from langgraph.types import Command
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from app.auth import get_current_user
from app.db import Application, ApplicationStatus, Profile, Resume, User, get_engine, get_session
from app.deps import get_graph
from app.schemas import ReviewDecision

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/applications", tags=["applications"])


class ApplicationCreate(BaseModel):
    resume_id: int | None = Field(default=None, description="Defaults to your active resume")
    job_text: str = Field(min_length=50, max_length=50_000, description="Full text of the job posting")
    job_url: str = Field("", max_length=2000)
    notes: str = Field("", max_length=5000)


class ApplicationUpdate(BaseModel):
    status: ApplicationStatus | None = None
    notes: str | None = Field(default=None, max_length=5000)
    company: str | None = Field(default=None, max_length=200)
    title: str | None = Field(default=None, max_length=200)


class ApplicationOut(BaseModel):
    id: int
    resume_id: int
    company: str
    title: str
    job_url: str
    status: ApplicationStatus
    fit_score: int | None
    notes: str
    created_at: datetime
    updated_at: datetime
    awaiting_review: bool = False
    agent: dict[str, Any] = Field(default_factory=dict)


# What the API returns from the agent's state (internal bookkeeping is left out).
AGENT_KEYS = ("job", "match", "bullets", "cover_letter", "outreach", "review_history")


def _config(row: Application) -> dict:
    return {"configurable": {"thread_id": row.thread_id}}


def _to_out(row: Application, graph, include_agent: bool = True) -> ApplicationOut:
    out = ApplicationOut.model_validate(row, from_attributes=True)
    if include_agent:
        snap = graph.get_state(_config(row))
        out.agent = {k: snap.values.get(k) for k in AGENT_KEYS if k in snap.values}
        out.awaiting_review = "human_review" in (snap.next or ())
    return out


def _sync_row(row: Application, graph, session: Session) -> None:
    """Copy useful fields from the agent's state onto the database row."""
    values = graph.get_state(_config(row)).values
    job, match = values.get("job") or {}, values.get("match") or {}
    row.company = row.company or job.get("company", "")
    row.title = row.title or job.get("title", "")
    if match:
        row.fit_score = match.get("fit_score")
    if values.get("status") == "approved" and row.status == ApplicationStatus.draft:
        row.status = ApplicationStatus.ready
    row.updated_at = datetime.now(UTC)
    session.add(row)
    session.commit()
    session.refresh(row)


def _run_agent(graph, payload, config) -> None:
    try:
        graph.invoke(payload, config)
    except Exception as e:  # OpenAI/network errors become 502 Bad Gateway
        log.exception("Agent run failed")
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Agent failed: {e}") from e


def _own_application(session: Session, user: User, app_id: int) -> Application:
    row = session.get(Application, app_id)
    if row is None or row.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Application not found")
    return row


def _new_application(session: Session, user: User, body: ApplicationCreate) -> tuple[Application, dict]:
    """Create the database row. Returns it with the resume profile the agent will use."""
    resume_id = body.resume_id
    if resume_id is None:
        profile = session.get(Profile, user.id)
        resume_id = profile.active_resume_id if profile else None
        if resume_id is None:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Upload your resume first")
    resume = session.get(Resume, resume_id)
    if resume is None or resume.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Resume not found")

    row = Application(
        user_id=user.id,
        resume_id=resume.id,
        thread_id=str(uuid.uuid4()),
        job_text=body.job_text,
        job_url=body.job_url,
        notes=body.notes,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row, resume.profile


@router.post("", response_model=ApplicationOut, status_code=status.HTTP_201_CREATED)
def create_application(
    body: ApplicationCreate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    graph=Depends(get_graph),
):
    row, resume_profile = _new_application(session, user, body)
    _run_agent(graph, {"resume": resume_profile, "job_text": body.job_text}, _config(row))
    _sync_row(row, graph, session)
    return _to_out(row, graph)


def _sse(event: dict) -> str:
    return f"data: {json.dumps(event, default=str)}\n\n"


@router.post("/stream")
def create_application_stream(
    body: ApplicationCreate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    graph=Depends(get_graph),
):
    """Events: {"type": "created", "id"} -> {"type": "node", "node"}... ->
    {"type": "done", "application"} or {"type": "error", "detail"}."""
    row, resume_profile = _new_application(session, user, body)
    app_id = row.id

    def events():
        yield _sse({"type": "created", "id": app_id})
        # A fresh session: the request's own session may be closed while we stream.
        with Session(get_engine()) as s:
            app_row = s.get(Application, app_id)
            try:
                for update in graph.stream(
                    {"resume": resume_profile, "job_text": body.job_text},
                    _config(app_row),
                    stream_mode="updates",
                ):
                    for node in update:
                        if node != "__interrupt__":
                            yield _sse({"type": "node", "node": node})
            except Exception as e:
                log.exception("Agent run failed")
                yield _sse({"type": "error", "detail": f"Agent failed: {e}"})
                return
            _sync_row(app_row, graph, s)
            yield _sse({"type": "done", "application": _to_out(app_row, graph).model_dump(mode="json")})

    return StreamingResponse(events(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


@router.post("/{app_id}/review", response_model=ApplicationOut)
def review_application(
    app_id: int,
    decision: ReviewDecision,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    graph=Depends(get_graph),
):
    row = _own_application(session, user, app_id)
    if "human_review" not in (graph.get_state(_config(row)).next or ()):
        raise HTTPException(status.HTTP_409_CONFLICT, "This application is not waiting for review")
    if decision.action == "revise" and not decision.target:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "`target` is required when action is 'revise'"
        )

    _run_agent(graph, Command(resume=decision.model_dump()), _config(row))
    _sync_row(row, graph, session)
    return _to_out(row, graph)


@router.get("", response_model=list[ApplicationOut])
def list_applications(
    status_filter: ApplicationStatus | None = Query(None, alias="status"),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    graph=Depends(get_graph),
):
    q = select(Application).where(Application.user_id == user.id).order_by(Application.updated_at.desc())
    if status_filter:
        q = q.where(Application.status == status_filter)
    return [_to_out(r, graph, include_agent=False) for r in session.exec(q).all()]


@router.get("/{app_id}", response_model=ApplicationOut)
def get_application(
    app_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    graph=Depends(get_graph),
):
    return _to_out(_own_application(session, user, app_id), graph)


@router.patch("/{app_id}", response_model=ApplicationOut)
def update_application(
    app_id: int,
    body: ApplicationUpdate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    graph=Depends(get_graph),
):
    row = _own_application(session, user, app_id)
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(row, k, v)
    row.updated_at = datetime.now(UTC)
    session.add(row)
    session.commit()
    session.refresh(row)
    return _to_out(row, graph)


@router.delete("/{app_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_application(
    app_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    graph=Depends(get_graph),
):
    row = _own_application(session, user, app_id)
    graph.checkpointer.delete_thread(row.thread_id)
    session.delete(row)
    session.commit()
