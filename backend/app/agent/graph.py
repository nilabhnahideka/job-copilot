"""
Graph topology:

    START
      │
  parse_job
      │
  match_resume ─────────────┬──────────────────┐
      │                     │                  │
  tailor_bullets ◄──┐  draft_cover_letter  draft_outreach     (run in parallel)
      │             │       │                  │
  check_grounding ──┘       │                  │   (retry if rewrites are ungrounded)
      │                     │                  │
  finalize_bullets          │                  │
      └──────────────┬──────┴──────────────────┘
                human_review  ◄────┐   (interrupt: waits for the user)
                     │             │
              approve│      revise │
                     ▼             │
                    END          revise
"""

from __future__ import annotations

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph

from app.agent import nodes
from app.agent.state import CopilotState


def build_graph(checkpointer: BaseCheckpointSaver | None = None):
    g = StateGraph(CopilotState)

    g.add_node("parse_job", nodes.parse_job)
    g.add_node("match_resume", nodes.match_resume)
    g.add_node("tailor_bullets", nodes.tailor_bullets)
    g.add_node("check_grounding", nodes.check_grounding)
    g.add_node("finalize_bullets", nodes.finalize_bullets)
    g.add_node("draft_cover_letter", nodes.draft_cover_letter)
    g.add_node("draft_outreach", nodes.draft_outreach)
    g.add_node("human_review", nodes.human_review)
    g.add_node("revise", nodes.revise)

    g.add_edge(START, "parse_job")
    g.add_edge("parse_job", "match_resume")

    # fan-out
    g.add_edge("match_resume", "tailor_bullets")
    g.add_edge("match_resume", "draft_cover_letter")
    g.add_edge("match_resume", "draft_outreach")

    # grounding self-correction loop
    g.add_edge("tailor_bullets", "check_grounding")
    g.add_conditional_edges(
        "check_grounding",
        nodes.route_after_grounding,
        {"tailor_bullets": "tailor_bullets", "finalize_bullets": "finalize_bullets"},
    )

    # fan-in: wait for all three branches
    g.add_edge(["finalize_bullets", "draft_cover_letter", "draft_outreach"], "human_review")

    g.add_conditional_edges("human_review", nodes.route_after_review, {"revise": "revise", "__end__": END})
    g.add_edge("revise", "human_review")

    return g.compile(checkpointer=checkpointer)
