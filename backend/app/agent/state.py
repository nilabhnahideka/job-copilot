"""Graph state.

Values are stored as plain JSON-compatible dicts/lists (not Pydantic objects) so
the SQLite checkpointer can always serialise and restore them safely.
"""

from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict


class CopilotState(TypedDict, total=False):
    # Inputs
    resume: dict[str, Any]  # ResumeProfile
    job_text: str

    # Analysis
    job: dict[str, Any]  # JobRequirements
    match: dict[str, Any]  # MatchReport

    # Tailored resume bullets + grounding loop
    bullets: list[dict[str, Any]]  # list[TailoredBullet]
    grounding_issues: list[dict[str, Any]]
    tailor_attempts: int

    # Drafts
    cover_letter: str
    outreach: str

    # Human-in-the-loop
    review_history: Annotated[list[dict[str, Any]], operator.add]
    last_review: dict[str, Any]
    status: str  # running | awaiting_review | approved
