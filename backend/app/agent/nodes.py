"""LangGraph nodes. Each node takes the state and returns a partial update."""

from __future__ import annotations

import json
import logging

from langgraph.types import interrupt

from app.agent import prompts
from app.agent.scoring import build_report, filter_known_originals
from app.agent.state import CopilotState
from app.config import get_settings
from app.llm import get_llm
from app.schemas import (
    CoverLetter,
    GroundingReport,
    JobRequirements,
    MatchAssessment,
    MatchReport,
    OutreachMessage,
    ResumeProfile,
    ReviewDecision,
    TailoredBullet,
    TailoredBullets,
)

log = logging.getLogger(__name__)


# --- helpers ---------------------------------------------------------------
def _resume(state: CopilotState) -> ResumeProfile:
    return ResumeProfile.model_validate(state["resume"])


def _job(state: CopilotState) -> JobRequirements:
    return JobRequirements.model_validate(state["job"])


def _match(state: CopilotState) -> MatchReport:
    return MatchReport.model_validate(state["match"])


def _resume_block(resume: ResumeProfile) -> str:
    return f"<resume>\n{resume.model_dump_json(indent=1)}\n</resume>"


def _job_block(job: JobRequirements) -> str:
    return f"<job>\n{job.model_dump_json(indent=1)}\n</job>"


def _context(state: CopilotState) -> str:
    m = _match(state)
    return (
        f"{_job_block(_job(state))}\n\n{_resume_block(_resume(state))}\n\n"
        f"Match analysis: strengths={m.strengths} gaps={m.gaps}"
    )


# --- analysis --------------------------------------------------------------
def parse_job(state: CopilotState) -> CopilotState:
    text = state["job_text"][: get_settings().max_job_chars]
    job = get_llm().structured(prompts.PARSE_JOB, f"<job>\n{text}\n</job>", JobRequirements)
    return {"job": job.model_dump(mode="json"), "status": "running", "tailor_attempts": 0}


def match_resume(state: CopilotState) -> CopilotState:
    resume, job = _resume(state), _job(state)
    reqs = "\n".join(f"- [{r.importance.value}] {r.text}" for r in job.requirements)
    assessment = get_llm().structured(
        prompts.MATCH,
        f"Requirements:\n{reqs}\n\n{_resume_block(resume)}",
        MatchAssessment,
    )
    report = build_report(assessment, job.keywords, resume)
    return {"match": report.model_dump(mode="json")}


# --- tailored bullets + grounding loop -------------------------------------
def tailor_bullets(state: CopilotState) -> CopilotState:
    resume = _resume(state)
    system = prompts.TAILOR
    if state.get("grounding_issues"):
        issues = "\n".join(f"- {i['rewritten']}: {i['problem']}" for i in state["grounding_issues"])
        system += prompts.TAILOR_RETRY_SUFFIX.format(issues=issues)

    result = get_llm().structured(system, _context(state), TailoredBullets)
    kept, dropped = filter_known_originals(result.bullets, resume)
    if dropped:
        log.warning("Dropped %d rewrites with unknown originals", len(dropped))
    return {
        "bullets": [b.model_dump() for b in kept],
        "tailor_attempts": state.get("tailor_attempts", 0) + 1,
    }


def check_grounding(state: CopilotState) -> CopilotState:
    bullets = state.get("bullets", [])
    if not bullets:
        return {"grounding_issues": []}
    pairs = json.dumps([{"original": b["original"], "rewritten": b["rewritten"]} for b in bullets], indent=1)
    report = get_llm().structured(prompts.GROUNDING, pairs, GroundingReport)
    return {"grounding_issues": [i.model_dump() for i in report.issues]}


def route_after_grounding(state: CopilotState) -> str:
    if state.get("grounding_issues") and state.get("tailor_attempts", 0) < get_settings().max_tailor_attempts:
        return "tailor_bullets"
    return "finalize_bullets"


def finalize_bullets(state: CopilotState) -> CopilotState:
    """If issues remain after max retries, drop the ungrounded rewrites rather than ship them."""
    bad = {i["rewritten"] for i in state.get("grounding_issues", [])}
    return {"bullets": [b for b in state.get("bullets", []) if b["rewritten"] not in bad]}


# --- drafts ----------------------------------------------------------------
def draft_cover_letter(state: CopilotState) -> CopilotState:
    letter = get_llm().structured(prompts.COVER_LETTER, _context(state), CoverLetter)
    return {"cover_letter": letter.text}


def draft_outreach(state: CopilotState) -> CopilotState:
    msg = get_llm().structured(prompts.OUTREACH, _context(state), OutreachMessage)
    return {"outreach": msg.text}


# --- human in the loop -----------------------------------------------------
def human_review(state: CopilotState) -> CopilotState:
    """Pause the graph. The API resumes it with Command(resume=ReviewDecision)."""
    raw = interrupt(
        {
            "message": "Review the drafts. Approve, or ask for a revision.",
            "targets": ["bullets", "cover_letter", "outreach"],
        }
    )
    decision = ReviewDecision.model_validate(raw)
    update: CopilotState = {
        "last_review": decision.model_dump(),
        "review_history": [decision.model_dump()],
    }
    if decision.action == "approve":
        update["status"] = "approved"
    return update


def route_after_review(state: CopilotState) -> str:
    return "revise" if state["last_review"]["action"] == "revise" else "__end__"


def revise(state: CopilotState) -> CopilotState:
    decision = ReviewDecision.model_validate(state["last_review"])
    llm, ctx = get_llm(), _context(state)
    feedback = f"Candidate feedback: {decision.feedback}"

    if decision.target == "bullets":
        current = json.dumps(state.get("bullets", []), indent=1)
        result = llm.structured(
            prompts.REVISE + "\n" + prompts.TAILOR,
            f"{ctx}\n\nCurrent bullets:\n{current}\n\n{feedback}",
            TailoredBullets,
        )
        kept, _ = filter_known_originals(result.bullets, _resume(state))
        return {"bullets": [TailoredBullet.model_validate(b).model_dump() for b in kept]}

    if decision.target == "outreach":
        msg = llm.structured(
            prompts.REVISE,
            f"{ctx}\n\nCurrent message:\n{state.get('outreach', '')}\n\n{feedback}",
            OutreachMessage,
        )
        return {"outreach": msg.text}

    # default: cover letter
    letter = llm.structured(
        prompts.REVISE,
        f"{ctx}\n\nCurrent cover letter:\n{state.get('cover_letter', '')}\n\n{feedback}",
        CoverLetter,
    )
    return {"cover_letter": letter.text}
