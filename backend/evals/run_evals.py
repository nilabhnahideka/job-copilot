"""Run the real agent (with your configured AI provider) against a small golden set.

    cd backend && python -m evals.run_evals

Checks per case:
  1. verdict      - fit verdict is in the expected range
  2. gaps         - expected gaps are surfaced (in gaps or missing requirements)
  3. grounded     - every tailored bullet's `original` really exists on the resume
  4. no_new_tools - rewritten bullets don't mention tech absent from the resume

Exits non-zero if any check fails, so it can gate CI on a schedule.
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

from langgraph.checkpoint.memory import InMemorySaver

from app.agent.graph import build_graph
from app.agent.scoring import resume_text
from app.resume_parser import parse_resume
from app.schemas import ResumeProfile

TECH_TERMS = [
    "python",
    "pytorch",
    "tensorflow",
    "langchain",
    "langgraph",
    "kubernetes",
    "aws",
    "gcp",
    "azure",
    "docker",
    "react",
    "fastapi",
    "django",
    "spark",
    "kafka",
    "redis",
    "postgresql",
    "pgvector",
    "openai",
    "streamlit",
    "langsmith",
    "terraform",
    "java",
    "golang",
    "rust",
]


def run_case(case: dict) -> dict:
    t0 = time.time()
    resume = parse_resume(case["resume"])
    graph = build_graph(InMemorySaver())
    cfg = {"configurable": {"thread_id": case["id"]}}
    graph.invoke({"resume": resume.model_dump(mode="json"), "job_text": case["job"]}, cfg)
    v = graph.get_state(cfg).values

    match = v["match"]
    gap_text = " ".join(
        match["gaps"] + [m["requirement"] for m in match["matches"] if m["level"] != "strong"]
    ).lower()

    profile = ResumeProfile.model_validate(v["resume"])
    on_resume = resume_text(profile)
    originals = {b.lower() for b in profile.all_bullets()}

    new_tools = []
    for b in v.get("bullets", []):
        for term in TECH_TERMS:
            pat = rf"\b{re.escape(term)}\b"
            if re.search(pat, b["rewritten"].lower()) and not re.search(pat, on_resume):
                new_tools.append(f"{term} in: {b['rewritten']}")

    checks = {
        "verdict": match["verdict"] in case["expect_verdict"],
        "gaps": all(g in gap_text for g in case["must_mention_gaps"]),
        "grounded": all(b["original"].lower() in originals for b in v.get("bullets", [])),
        "no_new_tools": not new_tools,
    }
    return {
        "id": case["id"],
        "score": match["fit_score"],
        "verdict": match["verdict"],
        "checks": checks,
        "new_tools": new_tools,
        "seconds": round(time.time() - t0, 1),
    }


def main() -> int:
    cases = json.loads((Path(__file__).parent / "cases.json").read_text())
    results = [run_case(c) for c in cases]
    failed = 0
    for r in results:
        ok = all(r["checks"].values())
        failed += not ok
        marks = " ".join(f"{k}={'✓' if v else '✗'}" for k, v in r["checks"].items())
        print(
            f"{'PASS' if ok else 'FAIL'}  {r['id']:<40} score={r['score']:<3} {r['verdict']:<11} {marks}  ({r['seconds']}s)"
        )
        for t in r["new_tools"]:
            print(f"      ungrounded tech -> {t}")
    print(f"\n{len(results) - failed}/{len(results)} cases passed")
    Path("evals/last_results.json").write_text(json.dumps(results, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
