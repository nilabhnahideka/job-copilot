"""Profile helpers shared by several endpoints."""

from __future__ import annotations

import re
from datetime import UTC, datetime

from sqlmodel import Session

from app.db import Profile
from app.profile_schema import ProfileData
from app.schemas import ResumeProfile


def get_or_create_profile(session: Session, user_id: int) -> Profile:
    profile = session.get(Profile, user_id)
    if profile is None:
        profile = Profile(user_id=user_id, data=ProfileData().model_dump(mode="json"))
        session.add(profile)
        session.flush()
    return profile


def question_key(question: str) -> str:
    """Normalise a form question so small differences don't create duplicates.

    "What is your Notice Period?" and "what is your notice period" -> same key.
    """
    text = re.sub(r"[^\w\s]", " ", question.lower())
    return re.sub(r"\s+", " ", text).strip()


def prefill_from_resume(profile: Profile, resume: ResumeProfile) -> list[str]:
    """Fill EMPTY profile fields from a parsed resume. Never overwrites what you typed.

    Returns the labels of the fields that were filled, so the website can tell you.
    """
    data = ProfileData.model_validate(profile.data)
    filled: list[str] = []

    def fill(obj, attr: str, value, label: str) -> None:
        if value and not getattr(obj, attr):
            setattr(obj, attr, value)
            filled.append(label)

    first, _, last = resume.name.strip().partition(" ")
    p = data.personal
    fill(p, "first_name", first, "First name")
    fill(p, "last_name", last.strip(), "Last name")
    fill(p, "email", resume.email, "Email")
    fill(p, "phone", resume.phone, "Phone")
    # The resume usually says "Bengaluru, Karnataka" or "Pune, India"; take the city part.
    fill(p, "city", resume.location.split(",")[0].strip(), "City")
    fill(p, "linkedin_url", resume.linkedin_url, "LinkedIn")
    fill(p, "github_url", resume.github_url, "GitHub")
    fill(p, "portfolio_url", resume.portfolio_url, "Portfolio")

    if resume.experience:
        latest = resume.experience[0]  # resumes list the most recent job first
        # Only treat it as your current job if it hasn't ended.
        ongoing = not latest.end or latest.end.strip().lower() in {"present", "current", "now", "till date"}
        if ongoing:
            fill(data.work, "current_company", latest.company, "Current company")
            fill(data.work, "current_title", latest.title, "Current title")
    fill(data.work, "skills", resume.skills, "Skills")

    if filled:
        profile.data = data.model_dump(mode="json")
        profile.updated_at = datetime.now(UTC)
    return filled
