"""FastAPI app: the HTTP API the website talks to.

This file only wires things together. The endpoints live in `app/routers/`:
- auth.py          sign up, log in
- profile.py       your profile and saved answers
- resumes.py       resume upload and download
- applications.py  run the agent on a job, review drafts, track applications

On startup it brings the database schema up to date (Alembic migrations) and
opens the checkpointer where the agent saves its progress.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

from app.agent.graph import build_graph
from app.checkpointer import open_checkpointer
from app.config import get_settings
from app.db import run_migrations
from app.deps import get_graph
from app.routers import applications, auth, profile, resumes

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("job-copilot")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    settings.validate_for_production()
    if settings.environment != "production" and settings.jwt_secret.startswith("dev-only"):
        log.warning("Using the development JWT secret. Set JWT_SECRET before deploying.")
    run_migrations()
    with open_checkpointer(settings) as checkpointer:
        app.state.graph = build_graph(checkpointer)
        yield


app = FastAPI(title="Job Copilot", version="0.3.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(resumes.router)
app.include_router(applications.router)


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/api/graph", response_class=PlainTextResponse)
def graph_mermaid(graph=Depends(get_graph)):
    """Mermaid diagram of the agent graph (handy for the README)."""
    return graph.get_graph().draw_mermaid()
