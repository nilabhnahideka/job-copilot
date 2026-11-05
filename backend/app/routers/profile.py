"""Your profile and saved answers.

GET    /api/profile                  your profile, the active resume, and what's still missing
PUT    /api/profile                  save the whole profile (every section)
PUT    /api/profile/active-resume    choose which uploaded resume to use

GET    /api/profile/answers          answers to extra form questions
POST   /api/profile/answers          add one (or update it if the same question exists)
PATCH  /api/profile/answers/{id}     edit one
DELETE /api/profile/answers/{id}     delete one
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from app.auth import get_current_user
from app.db import Resume, SavedAnswer, User, get_session
from app.profile_schema import ProfileData, missing_for_applying
from app.profile_service import get_or_create_profile, question_key

router = APIRouter(prefix="/api/profile", tags=["profile"])


class ResumeSummary(BaseModel):
    id: int
    label: str
    file_name: str
    created_at: datetime


class ProfileOut(BaseModel):
    data: ProfileData
    active_resume: ResumeSummary | None
    missing: list[str] = Field(description="What still needs filling before the app can apply for you")
    updated_at: datetime


def _profile_out(session: Session, user_id: int) -> ProfileOut:
    profile = get_or_create_profile(session, user_id)
    resume = session.get(Resume, profile.active_resume_id) if profile.active_resume_id else None
    data = ProfileData.model_validate(profile.data)
    return ProfileOut(
        data=data,
        active_resume=ResumeSummary.model_validate(resume, from_attributes=True) if resume else None,
        missing=missing_for_applying(data, has_resume=resume is not None),
        updated_at=profile.updated_at,
    )


@router.get("", response_model=ProfileOut)
def get_profile(user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    out = _profile_out(session, user.id)
    session.commit()  # saves the empty profile if this is the first visit
    return out


@router.put("", response_model=ProfileOut)
def save_profile(
    body: ProfileData, user: User = Depends(get_current_user), session: Session = Depends(get_session)
):
    profile = get_or_create_profile(session, user.id)
    profile.data = body.model_dump(mode="json")
    profile.updated_at = datetime.now(UTC)
    session.add(profile)
    session.commit()
    return _profile_out(session, user.id)


class ActiveResumeIn(BaseModel):
    resume_id: int


@router.put("/active-resume", response_model=ProfileOut)
def set_active_resume(
    body: ActiveResumeIn, user: User = Depends(get_current_user), session: Session = Depends(get_session)
):
    resume = session.get(Resume, body.resume_id)
    if resume is None or resume.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Resume not found")
    profile = get_or_create_profile(session, user.id)
    profile.active_resume_id = resume.id
    profile.updated_at = datetime.now(UTC)
    session.add(profile)
    session.commit()
    return _profile_out(session, user.id)


# --- saved answers ----------------------------------------------------------
class AnswerIn(BaseModel):
    question: str = Field(min_length=2, max_length=500)
    answer: str = Field(min_length=1, max_length=5000)
    source: Literal["manual", "application"] = "manual"


class AnswerPatch(BaseModel):
    question: str | None = Field(default=None, min_length=2, max_length=500)
    answer: str | None = Field(default=None, min_length=1, max_length=5000)


class AnswerOut(BaseModel):
    id: int
    question: str
    answer: str
    source: str
    updated_at: datetime


def _own_answer(session: Session, user: User, answer_id: int) -> SavedAnswer:
    row = session.get(SavedAnswer, answer_id)
    if row is None or row.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Answer not found")
    return row


@router.get("/answers", response_model=list[AnswerOut])
def list_answers(user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    rows = session.exec(
        select(SavedAnswer).where(SavedAnswer.user_id == user.id).order_by(SavedAnswer.updated_at.desc())
    ).all()
    return [AnswerOut.model_validate(r, from_attributes=True) for r in rows]


@router.post("/answers", response_model=AnswerOut, status_code=status.HTTP_201_CREATED)
def add_answer(
    body: AnswerIn, user: User = Depends(get_current_user), session: Session = Depends(get_session)
):
    key = question_key(body.question)
    row = session.exec(
        select(SavedAnswer).where(SavedAnswer.user_id == user.id, SavedAnswer.question_key == key)
    ).first()
    if row is None:
        row = SavedAnswer(user_id=user.id, question=body.question.strip(), question_key=key, answer="")
    row.answer = body.answer.strip()
    row.source = body.source
    row.updated_at = datetime.now(UTC)
    session.add(row)
    session.commit()
    session.refresh(row)
    return AnswerOut.model_validate(row, from_attributes=True)


@router.patch("/answers/{answer_id}", response_model=AnswerOut)
def edit_answer(
    answer_id: int,
    body: AnswerPatch,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    row = _own_answer(session, user, answer_id)
    if body.question is not None:
        key = question_key(body.question)
        clash = session.exec(
            select(SavedAnswer).where(
                SavedAnswer.user_id == user.id, SavedAnswer.question_key == key, SavedAnswer.id != row.id
            )
        ).first()
        if clash:
            raise HTTPException(status.HTTP_409_CONFLICT, "You already have an answer for that question")
        row.question, row.question_key = body.question.strip(), key
    if body.answer is not None:
        row.answer = body.answer.strip()
    row.updated_at = datetime.now(UTC)
    session.add(row)
    session.commit()
    session.refresh(row)
    return AnswerOut.model_validate(row, from_attributes=True)


@router.delete("/answers/{answer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_answer(
    answer_id: int, user: User = Depends(get_current_user), session: Session = Depends(get_session)
):
    session.delete(_own_answer(session, user, answer_id))
    session.commit()
