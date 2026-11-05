from __future__ import annotations

import logging
import sqlite3
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from app.agent.graph import build_graph
from app.config import get_settings
from app.db import Application, ApplicationStatus, Resume, get_session, init_db
from app.resume_parser import extract_pdf_text, parse_resume
from app.schemas import ResumeProfile, ReviewDecision

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("job-copilot")


@asynccontextmanager
async def lifespan(app: FastAPI):
    s = get_settings()
    init_db()
    Path(s.checkpoint_db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(s.checkpoint_db_path, check_same_thread=False)
    app.state.graph = build_graph(SqliteSaver(conn))
    yield
    conn.close()


app = FastAPI(title="Job Application Copilot", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_graph(request: Request):
    return request.app.state.graph


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------
class ResumeOut(BaseModel):
    id: int
    label: str
    profile: ResumeProfile
    created_at: datetime


class ApplicationCreate(BaseModel):
    resume_id: int
    job_text: str = Field(min_length=50, description="Full text of the job posting")
    job_url: str = ""
    notes: str = ""


class ApplicationUpdate(BaseModel):
    status: ApplicationStatus | None = None
    notes: str | None = None
    company: str | None = None
    title: str | None = None


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


AGENT_KEYS = ("job", "match", "bullets", "cover_letter", "outreach", "review_history")


def _config(app_row: Application) -> dict:
    return {"configurable": {"thread_id": app_row.thread_id}}


def _to_out(row: Application, graph, include_agent: bool = True) -> ApplicationOut:
    out = ApplicationOut.model_validate(row, from_attributes=True)
    if include_agent:
        snap = graph.get_state(_config(row))
        out.agent = {k: snap.values.get(k) for k in AGENT_KEYS if k in snap.values}
        out.awaiting_review = "human_review" in (snap.next or ())
    return out


def _sync_row(row: Application, graph, session: Session) -> None:
    """Copy useful fields from agent state onto the DB row."""
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
    except Exception as e:  # LLM/provider errors surface as 502
        log.exception("Agent run failed")
        raise HTTPException(502, f"Agent failed: {e}") from e


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/health")
def health():
    return {"ok": True}


@app.get("/api/graph", response_class=PlainTextResponse)
def graph_mermaid(graph=Depends(get_graph)):
    """Mermaid diagram of the agent graph (handy for the README)."""
    return graph.get_graph().draw_mermaid()


@app.post("/api/resumes", response_model=ResumeOut)
async def upload_resume(
    file: UploadFile | None = File(None),
    text: str | None = Form(None),
    label: str = Form("My resume"),
    session: Session = Depends(get_session),
):
    if file is not None:
        data = await file.read()
        if len(data) > 5 * 1024 * 1024:
            raise HTTPException(413, "Resume file too large (max 5MB)")
        try:
            raw = extract_pdf_text(data) if (file.filename or "").lower().endswith(".pdf") else data.decode()
        except (ValueError, UnicodeDecodeError) as e:
            raise HTTPException(422, str(e)) from e
    elif text:
        raw = text
    else:
        raise HTTPException(422, "Provide a PDF/TXT file or a `text` field")

    try:
        profile = parse_resume(raw)
    except Exception as e:
        log.exception("Resume parsing failed")
        raise HTTPException(502, f"Resume parsing failed: {e}") from e

    row = Resume(label=label, raw_text=raw, profile=profile.model_dump(mode="json"))
    session.add(row)
    session.commit()
    session.refresh(row)
    return ResumeOut(id=row.id, label=row.label, profile=profile, created_at=row.created_at)


@app.get("/api/resumes", response_model=list[ResumeOut])
def list_resumes(session: Session = Depends(get_session)):
    rows = session.exec(select(Resume).order_by(Resume.created_at.desc())).all()
    return [
        ResumeOut(
            id=r.id, label=r.label, profile=ResumeProfile.model_validate(r.profile), created_at=r.created_at
        )
        for r in rows
    ]


@app.post("/api/applications", response_model=ApplicationOut, status_code=201)
def create_application(
    body: ApplicationCreate, session: Session = Depends(get_session), graph=Depends(get_graph)
):
    resume = session.get(Resume, body.resume_id)
    if not resume:
        raise HTTPException(404, "Resume not found")

    row = Application(
        resume_id=resume.id,
        thread_id=str(uuid.uuid4()),
        job_text=body.job_text,
        job_url=body.job_url,
        notes=body.notes,
    )
    session.add(row)
    session.commit()
    session.refresh(row)

    _run_agent(graph, {"resume": resume.profile, "job_text": body.job_text}, _config(row))
    _sync_row(row, graph, session)
    return _to_out(row, graph)


@app.post("/api/applications/{app_id}/review", response_model=ApplicationOut)
def review_application(
    app_id: int,
    decision: ReviewDecision,
    session: Session = Depends(get_session),
    graph=Depends(get_graph),
):
    row = session.get(Application, app_id)
    if not row:
        raise HTTPException(404, "Application not found")
    if "human_review" not in (graph.get_state(_config(row)).next or ()):
        raise HTTPException(409, "This application is not waiting for review")
    if decision.action == "revise" and not decision.target:
        raise HTTPException(422, "`target` is required when action is 'revise'")

    _run_agent(graph, Command(resume=decision.model_dump()), _config(row))
    _sync_row(row, graph, session)
    return _to_out(row, graph)


@app.get("/api/applications", response_model=list[ApplicationOut])
def list_applications(
    status: ApplicationStatus | None = None,
    session: Session = Depends(get_session),
    graph=Depends(get_graph),
):
    q = select(Application).order_by(Application.updated_at.desc())
    if status:
        q = q.where(Application.status == status)
    return [_to_out(r, graph, include_agent=False) for r in session.exec(q).all()]


@app.get("/api/applications/{app_id}", response_model=ApplicationOut)
def get_application(app_id: int, session: Session = Depends(get_session), graph=Depends(get_graph)):
    row = session.get(Application, app_id)
    if not row:
        raise HTTPException(404, "Application not found")
    return _to_out(row, graph)


@app.patch("/api/applications/{app_id}", response_model=ApplicationOut)
def update_application(
    app_id: int,
    body: ApplicationUpdate,
    session: Session = Depends(get_session),
    graph=Depends(get_graph),
):
    row = session.get(Application, app_id)
    if not row:
        raise HTTPException(404, "Application not found")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(row, k, v)
    row.updated_at = datetime.now(UTC)
    session.add(row)
    session.commit()
    session.refresh(row)
    return _to_out(row, graph)


@app.delete("/api/applications/{app_id}", status_code=204)
def delete_application(app_id: int, session: Session = Depends(get_session), graph=Depends(get_graph)):
    row = session.get(Application, app_id)
    if not row:
        raise HTTPException(404, "Application not found")
    graph.checkpointer.delete_thread(row.thread_id)
    session.delete(row)
    session.commit()
