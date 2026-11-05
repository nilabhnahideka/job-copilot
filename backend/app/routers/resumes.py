"""Resumes.

POST /api/resumes              upload a PDF/TXT file or paste text. It becomes your active
                               resume, and empty profile fields are filled in from it.
GET  /api/resumes              all your uploaded resumes, newest first
GET  /api/resumes/{id}         one resume with its parsed profile
GET  /api/resumes/{id}/file    download the original file
"""

from __future__ import annotations

import logging
from datetime import datetime
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from app.auth import get_current_user
from app.db import Resume, User, get_session
from app.profile_service import get_or_create_profile, prefill_from_resume
from app.resume_parser import extract_pdf_text, parse_resume
from app.schemas import ResumeProfile

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/resumes", tags=["resumes"])

MAX_FILE_BYTES = 5 * 1024 * 1024


class ResumeOut(BaseModel):
    id: int
    label: str
    file_name: str
    has_file: bool
    profile: ResumeProfile
    created_at: datetime


class UploadOut(ResumeOut):
    prefilled: list[str] = Field(default_factory=list, description="Profile fields filled from this resume")


def _out(r: Resume) -> ResumeOut:
    return ResumeOut(
        id=r.id,
        label=r.label,
        file_name=r.file_name,
        has_file=r.file_data is not None,
        profile=ResumeProfile.model_validate(r.profile),
        created_at=r.created_at,
    )


def _own_resume(session: Session, user: User, resume_id: int) -> Resume:
    row = session.get(Resume, resume_id)
    if row is None or row.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Resume not found")
    return row


@router.post("", response_model=UploadOut, status_code=status.HTTP_201_CREATED)
async def upload_resume(
    file: UploadFile | None = File(None),
    text: str | None = Form(None),
    label: str = Form("My resume", max_length=100),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    data: bytes | None = None
    name = ""
    if file is not None:
        data = await file.read()
        name = (file.filename or "resume").rsplit("/", 1)[-1]
        if len(data) > MAX_FILE_BYTES:
            raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Resume file too large (max 5 MB)")
        try:
            if name.lower().endswith(".pdf"):
                if not data.startswith(b"%PDF"):
                    raise ValueError("That file isn't a valid PDF")
                raw, content_type = extract_pdf_text(data), "application/pdf"
            elif name.lower().endswith(".txt"):
                raw, content_type = data.decode(), "text/plain"
            else:
                raise ValueError("Upload a .pdf or .txt file")
        except (ValueError, UnicodeDecodeError) as e:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(e)) from e
    elif text and text.strip():
        raw, content_type = text, ""
    else:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "Upload a PDF/TXT file or paste your resume text"
        )

    try:
        parsed = parse_resume(raw)
    except Exception as e:
        log.exception("Resume parsing failed")
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Resume parsing failed: {e}") from e

    row = Resume(
        user_id=user.id,
        label=label,
        raw_text=raw,
        profile=parsed.model_dump(mode="json"),
        file_name=name,
        content_type=content_type,
        file_data=data,
    )
    session.add(row)
    session.flush()

    # The newest upload becomes the one used for applications.
    profile = get_or_create_profile(session, user.id)
    profile.active_resume_id = row.id
    filled = prefill_from_resume(profile, parsed)
    session.add(profile)
    session.commit()
    session.refresh(row)
    return UploadOut(**_out(row).model_dump(), prefilled=filled)


@router.get("", response_model=list[ResumeOut])
def list_resumes(user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    rows = session.exec(
        select(Resume).where(Resume.user_id == user.id).order_by(Resume.created_at.desc())
    ).all()
    return [_out(r) for r in rows]


@router.get("/{resume_id}", response_model=ResumeOut)
def get_resume(
    resume_id: int, user: User = Depends(get_current_user), session: Session = Depends(get_session)
):
    return _out(_own_resume(session, user, resume_id))


@router.get("/{resume_id}/file")
def download_resume(
    resume_id: int, user: User = Depends(get_current_user), session: Session = Depends(get_session)
):
    row = _own_resume(session, user, resume_id)
    if row.file_data is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "This resume was pasted as text, so there's no file")
    return Response(
        content=row.file_data,
        media_type=row.content_type or "application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(row.file_name)}"},
    )
