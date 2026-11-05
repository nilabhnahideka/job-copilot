"""Deterministic fake LLM so the whole graph can be tested offline and for free."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable

from pydantic import BaseModel

from app.schemas import (
    CoverLetter,
    Experience,
    GroundingIssue,
    GroundingReport,
    Importance,
    JobRequirements,
    MatchAssessment,
    MatchLevel,
    OutreachMessage,
    Project,
    Requirement,
    RequirementMatch,
    ResumeProfile,
    TailoredBullet,
    TailoredBullets,
)

BULLET_1 = "Built a RAG chatbot over 2k internal docs using LangChain and FAISS"
BULLET_2 = "Wrote REST APIs in FastAPI serving 50k requests/day"
BULLET_3 = "Automated weekly reporting with Python and SQL, saving 6 hours per week"

RESUME = ResumeProfile(
    name="Asha Verma",
    headline="Software Engineer",
    email="asha.verma@example.com",
    phone="+91 98765 43210",
    location="Pune, Maharashtra",
    linkedin_url="https://linkedin.com/in/ashaverma",
    skills=["Python", "FastAPI", "LangChain", "SQL", "Docker"],
    experience=[Experience(title="Software Engineer", company="Acme", bullets=[BULLET_2, BULLET_3])],
    projects=[Project(name="DocBot", tech=["LangChain", "FAISS"], bullets=[BULLET_1])],
)

JOB = JobRequirements(
    title="GenAI Engineer",
    company="Nimbus AI",
    summary="Build LLM agents.",
    requirements=[
        Requirement(text="Python", category="skill", importance=Importance.must_have),
        Requirement(text="LLM application development", category="skill", importance=Importance.must_have),
        Requirement(text="Kubernetes", category="skill", importance=Importance.nice_to_have),
    ],
    keywords=["Python", "LangGraph", "RAG", "Kubernetes"],
)

MATCH = MatchAssessment(
    matches=[
        RequirementMatch(
            requirement="Python",
            importance=Importance.must_have,
            level=MatchLevel.strong,
            evidence="Python, FastAPI",
        ),
        RequirementMatch(
            requirement="LLM application development",
            importance=Importance.must_have,
            level=MatchLevel.partial,
            evidence="RAG chatbot",
        ),
        RequirementMatch(
            requirement="Kubernetes", importance=Importance.nice_to_have, level=MatchLevel.missing
        ),
    ],
    strengths=["Python backend"],
    gaps=["No agent frameworks"],
    suggestions=["Build a LangGraph project"],
)

GOOD_BULLETS = TailoredBullets(
    bullets=[
        TailoredBullet(
            original=BULLET_1,
            rewritten="Built a retrieval-augmented LLM chatbot over 2k docs with LangChain and FAISS",
            reason="LLM apps",
        ),
        TailoredBullet(
            original=BULLET_2,
            rewritten="Designed FastAPI REST services handling 50k requests/day",
            reason="Python",
        ),
    ]
)

HALLUCINATED = TailoredBullet(
    original=BULLET_3,
    rewritten="Led a team of 10 to automate reporting with Spark, saving $1M",
    reason="leadership",
)


class FakeLLM:
    """Responds based on the requested schema. Override per-test via `responses`."""

    def __init__(self, responses: dict[type, Callable[[str, str], BaseModel]] | None = None):
        self.calls: dict[type, int] = defaultdict(int)
        self.prompts: list[tuple[type, str, str]] = []
        self.responses: dict[type, Callable[[str, str], BaseModel]] = {
            ResumeProfile: lambda s, u: RESUME,
            JobRequirements: lambda s, u: JOB,
            MatchAssessment: lambda s, u: MATCH,
            TailoredBullets: lambda s, u: GOOD_BULLETS,
            GroundingReport: lambda s, u: GroundingReport(),
            CoverLetter: lambda s, u: CoverLetter(text="Dear Nimbus AI team, ... Asha"),
            OutreachMessage: lambda s, u: OutreachMessage(
                text="Hi [Name], I'm applying for GenAI Engineer..."
            ),
        }
        if responses:
            self.responses.update(responses)

    def structured(self, system, user, schema):
        self.calls[schema] += 1
        self.prompts.append((schema, system, user))
        return self.responses[schema](system, user)


def hallucinate_then_fix():
    """TailoredBullets returns a hallucinated bullet first, a clean set after feedback."""

    def tailor(system, user):
        if "fact-checker rejected" in system:
            return GOOD_BULLETS
        return TailoredBullets(bullets=[*GOOD_BULLETS.bullets, HALLUCINATED])

    def ground(system, user):
        if HALLUCINATED.rewritten in user:
            return GroundingReport(
                issues=[
                    GroundingIssue(
                        rewritten=HALLUCINATED.rewritten, problem="team size, Spark and $1M not in original"
                    )
                ]
            )
        return GroundingReport()

    return {TailoredBullets: tailor, GroundingReport: ground}


def make_pdf(text: str) -> bytes:
    """A minimal but valid one-page PDF containing `text`, for upload tests."""
    stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out, offsets = b"%PDF-1.4\n", []
    for i, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    out += b"".join(f"{o:010d} 00000 n \n".encode() for o in offsets)
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return out
