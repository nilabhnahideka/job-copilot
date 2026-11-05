"""Deterministic scoring and checks.

The LLM *classifies* each requirement (strong / partial / missing); plain code
turns that into a score. This keeps the score explainable, stable across runs
and cheap to unit-test, instead of asking the model to "rate the fit 0-100".
"""

from __future__ import annotations

import re

from app.schemas import (
    Importance,
    MatchAssessment,
    MatchLevel,
    MatchReport,
    ResumeProfile,
    TailoredBullet,
)

IMPORTANCE_WEIGHT = {Importance.must_have: 2.0, Importance.nice_to_have: 1.0}
LEVEL_CREDIT = {MatchLevel.strong: 1.0, MatchLevel.partial: 0.5, MatchLevel.missing: 0.0}


def fit_score(assessment: MatchAssessment) -> int:
    total = sum(IMPORTANCE_WEIGHT[m.importance] for m in assessment.matches)
    if total == 0:
        return 0
    earned = sum(IMPORTANCE_WEIGHT[m.importance] * LEVEL_CREDIT[m.level] for m in assessment.matches)
    score = round(100 * earned / total)

    # A missing must-have is a hard blocker for many recruiters: cap the score.
    missing_must = sum(
        1
        for m in assessment.matches
        if m.importance == Importance.must_have and m.level == MatchLevel.missing
    )
    if missing_must >= 2:
        score = min(score, 59)
    return score


def verdict(score: int) -> str:
    if score >= 80:
        return "strong_fit"
    if score >= 65:
        return "good_fit"
    if score >= 45:
        return "stretch"
    return "poor_fit"


def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def resume_text(resume: ResumeProfile) -> str:
    parts = [resume.headline, resume.summary, " ".join(resume.skills), " ".join(resume.education)]
    for e in resume.experience:
        parts += [e.title, e.company, *e.bullets]
    for p in resume.projects:
        parts += [p.name, p.description, " ".join(p.tech), *p.bullets]
    return _normalise(" ".join(parts))


def missing_keywords(keywords: list[str], resume: ResumeProfile) -> list[str]:
    haystack = resume_text(resume)
    out = []
    for kw in keywords:
        k = _normalise(kw)
        if not k:
            continue
        # word-boundary match so "Go" doesn't match "good"
        if not re.search(rf"(?<![a-z0-9]){re.escape(k)}(?![a-z0-9])", haystack):
            out.append(kw)
    return out


def build_report(assessment: MatchAssessment, keywords: list[str], resume: ResumeProfile) -> MatchReport:
    score = fit_score(assessment)
    return MatchReport(
        **assessment.model_dump(),
        fit_score=score,
        verdict=verdict(score),  # type: ignore[arg-type]
        missing_keywords=missing_keywords(keywords, resume),
    )


def filter_known_originals(
    bullets: list[TailoredBullet], resume: ResumeProfile
) -> tuple[list[TailoredBullet], list[TailoredBullet]]:
    """Drop rewrites whose `original` is not actually a bullet on the resume."""
    known = {_normalise(b) for b in resume.all_bullets()}
    kept, dropped = [], []
    for b in bullets:
        (kept if _normalise(b.original) in known else dropped).append(b)
    return kept, dropped
