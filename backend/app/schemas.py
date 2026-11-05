"""Pydantic models shared by the agent, the API and the LLM structured outputs."""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Resume
# ---------------------------------------------------------------------------
class Experience(BaseModel):
    title: str
    company: str
    start: str | None = None
    end: str | None = None
    bullets: list[str] = Field(default_factory=list)


class Project(BaseModel):
    name: str
    description: str = ""
    tech: list[str] = Field(default_factory=list)
    bullets: list[str] = Field(default_factory=list)


class ResumeProfile(BaseModel):
    """Structured version of a candidate's resume."""

    name: str = ""
    headline: str = ""
    summary: str = ""
    # Contact details, used to pre-fill your profile
    email: str = ""
    phone: str = ""
    location: str = Field("", description="City (and state/country) as written on the resume")
    linkedin_url: str = ""
    github_url: str = ""
    portfolio_url: str = ""
    skills: list[str] = Field(default_factory=list)
    experience: list[Experience] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    education: list[str] = Field(default_factory=list)

    def all_bullets(self) -> list[str]:
        out: list[str] = []
        for e in self.experience:
            out.extend(e.bullets)
        for p in self.projects:
            out.extend(p.bullets)
        return out


# ---------------------------------------------------------------------------
# Job
# ---------------------------------------------------------------------------
class Importance(str, Enum):
    must_have = "must_have"
    nice_to_have = "nice_to_have"


class Requirement(BaseModel):
    text: str = Field(description="One concrete requirement, e.g. '3+ years Python'")
    category: Literal["skill", "experience", "education", "domain", "soft_skill", "other"]
    importance: Importance


class JobRequirements(BaseModel):
    title: str = ""
    company: str = ""
    seniority: str = ""
    summary: str = Field("", description="Two-sentence summary of the role")
    requirements: list[Requirement] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list, description="ATS keywords")


# ---------------------------------------------------------------------------
# Matching
# ---------------------------------------------------------------------------
class MatchLevel(str, Enum):
    strong = "strong"
    partial = "partial"
    missing = "missing"


class RequirementMatch(BaseModel):
    requirement: str
    importance: Importance
    level: MatchLevel
    evidence: str = Field("", description="Quote or paraphrase from the resume; empty if missing")


class MatchAssessment(BaseModel):
    """What the LLM returns. The numeric score is computed in code, not by the LLM."""

    matches: list[RequirementMatch]
    strengths: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list, description="Missing or weak areas")
    suggestions: list[str] = Field(
        default_factory=list, description="Concrete ways to close gaps (learn X, highlight Y)"
    )


class MatchReport(MatchAssessment):
    fit_score: int = Field(ge=0, le=100)
    verdict: Literal["strong_fit", "good_fit", "stretch", "poor_fit"]
    missing_keywords: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Generated documents
# ---------------------------------------------------------------------------
class TailoredBullet(BaseModel):
    original: str = Field(description="The exact original resume bullet being rewritten")
    rewritten: str
    reason: str = Field("", description="Which job requirement this targets")


class TailoredBullets(BaseModel):
    bullets: list[TailoredBullet]


class GroundingIssue(BaseModel):
    rewritten: str
    problem: str = Field(description="What claim is not supported by the original resume")


class GroundingReport(BaseModel):
    issues: list[GroundingIssue] = Field(default_factory=list)


class CoverLetter(BaseModel):
    text: str


class OutreachMessage(BaseModel):
    text: str = Field(description="Short LinkedIn/email note to a recruiter, < 120 words")


ReviewTarget = Literal["bullets", "cover_letter", "outreach"]


class ReviewDecision(BaseModel):
    action: Literal["approve", "revise"]
    target: ReviewTarget | None = None
    feedback: str = ""
