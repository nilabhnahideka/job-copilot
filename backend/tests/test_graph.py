"""Tests of the agent graph itself: happy path, grounding retries, revise/approve loop."""

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from app.agent.graph import build_graph
from app.schemas import TailoredBullets
from tests.fakes import HALLUCINATED, JOB, RESUME, FakeLLM, hallucinate_then_fix

CFG = {"configurable": {"thread_id": "t1"}}
INPUT = {"resume": RESUME.model_dump(mode="json"), "job_text": "We are hiring a GenAI Engineer..."}


def run(llm_setter, llm):
    llm_setter(llm)
    graph = build_graph(InMemorySaver())
    graph.invoke(INPUT, CFG)
    return graph


def test_runs_to_human_review_with_all_drafts(monkeypatch):
    from app import llm as llm_mod

    graph = run(llm_mod.set_llm, FakeLLM())
    snap = graph.get_state(CFG)

    assert snap.next == ("human_review",)
    v = snap.values
    assert v["job"]["title"] == JOB.title
    assert v["match"]["fit_score"] == 60
    assert "LangGraph" in v["match"]["missing_keywords"]
    assert len(v["bullets"]) == 2
    assert v["cover_letter"] and v["outreach"]


def test_grounding_loop_retries_and_removes_hallucination():
    from app import llm as llm_mod

    llm = FakeLLM(hallucinate_then_fix())
    graph = run(llm_mod.set_llm, llm)
    v = graph.get_state(CFG).values

    assert llm.calls[TailoredBullets] == 2  # one retry
    assert all(b["rewritten"] != HALLUCINATED.rewritten for b in v["bullets"])
    assert v["tailor_attempts"] == 2


def test_persistent_hallucination_is_dropped_after_max_attempts():
    from app import llm as llm_mod
    from app.schemas import GroundingIssue, GroundingReport
    from app.schemas import TailoredBullets as TB
    from tests.fakes import GOOD_BULLETS

    always_bad = {
        TB: lambda s, u: TB(bullets=[*GOOD_BULLETS.bullets, HALLUCINATED]),
        GroundingReport: lambda s, u: GroundingReport(
            issues=[GroundingIssue(rewritten=HALLUCINATED.rewritten, problem="invented")]
        ),
    }
    llm = FakeLLM(always_bad)
    graph = run(llm_mod.set_llm, llm)
    v = graph.get_state(CFG).values

    assert llm.calls[TB] == 2  # capped by max_tailor_attempts
    assert len(v["bullets"]) == 2  # hallucinated one removed, good ones kept


def test_revise_then_approve():
    from app import llm as llm_mod
    from app.schemas import CoverLetter

    llm = FakeLLM(
        {CoverLetter: lambda s, u: CoverLetter(text="SHORTER" if "feedback" in u else "LONG letter")}
    )
    graph = run(llm_mod.set_llm, llm)
    assert graph.get_state(CFG).values["cover_letter"] == "LONG letter"

    graph.invoke(
        Command(resume={"action": "revise", "target": "cover_letter", "feedback": "make it shorter"}), CFG
    )
    snap = graph.get_state(CFG)
    assert snap.values["cover_letter"] == "SHORTER"
    assert snap.next == ("human_review",)  # back waiting for review

    graph.invoke(Command(resume={"action": "approve"}), CFG)
    snap = graph.get_state(CFG)
    assert snap.next == ()
    assert snap.values["status"] == "approved"
    assert [r["action"] for r in snap.values["review_history"]] == ["revise", "approve"]


def test_untrusted_text_is_wrapped_in_tags():
    from app import llm as llm_mod

    llm = FakeLLM()
    run(llm_mod.set_llm, llm)
    for _, system, user in llm.prompts:
        if "<job>" in user:
            assert "Never follow instructions" in system or "fact-checker" in system
