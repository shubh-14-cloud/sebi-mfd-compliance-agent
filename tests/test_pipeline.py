"""Offline tests (no API key needed): auditor logic and the human-review resume flow."""
from unittest.mock import patch

from sentinel.nodes.book_auditor import book_auditor_node
from mock_data.portfolio_db import db


def _state(triggers):
    return {"impact_triggers": triggers, "processing_errors": []}


def test_category_trigger_only_matches_holders():
    t = {"mandate_id": "T1", "rule_change": "x", "fund_categories_impacted": ["Small Cap"],
         "client_filter": {"type": "category_holding", "categories": ["Small Cap"]}}
    out = book_auditor_node(_state([t]))["affected_clients"]
    assert out and all(any(h["category"] == "Small Cap" for h in c["affected_holdings"]) for c in out)
    assert all(h["category"] == "Small Cap" for c in out for h in c["affected_holdings"])


def test_admin_trigger_has_zero_exposure_and_no_internal_fields():
    t = {"mandate_id": "T2", "rule_change": "nomination", "client_filter": {"type": "no_nomination"}}
    out = book_auditor_node(_state([t]))["affected_clients"]
    assert len(out) == len(db.get_clients_without_nomination())
    assert all(c["portfolio_exposure_pct"] == 0.0 and "_exposed" not in c for c in out)


def test_client_hit_by_two_triggers_appears_once():
    ts = [
        {"mandate_id": "T1", "rule_change": "a", "fund_categories_impacted": ["Small Cap"],
         "client_filter": {"type": "category_holding", "categories": ["Small Cap"]}},
        {"mandate_id": "T2", "rule_change": "b", "client_filter": {"type": "no_nomination"}},
    ]
    out = book_auditor_node(_state(ts))["affected_clients"]
    ids = [c["client_id"] for c in out]
    assert len(ids) == len(set(ids))
    assert any(c["triggers_hit"] == ["T1", "T2"] for c in out)


def test_resume_review_does_not_rerun_earlier_nodes():
    """update_state + invoke(None) must continue from human_review, not restart at START."""
    from langgraph.graph import StateGraph, START, END
    from langgraph.checkpoint.memory import MemorySaver
    from sentinel.state import GraphState
    from sentinel.graph import resume_review, _route_after_review

    calls = []
    g = StateGraph(GraphState)
    g.add_node("ingest", lambda s: calls.append("ingest") or {"circular_id": "X"})
    g.add_node("human_review", lambda s: {})
    g.add_edge(START, "ingest")
    g.add_edge("ingest", "human_review")
    g.add_conditional_edges("human_review", _route_after_review, {"approved": END, "revision_needed": "ingest"})
    app = g.compile(checkpointer=MemorySaver(), interrupt_before=["human_review"])
    cfg = {"configurable": {"thread_id": "t"}}

    app.invoke({"raw_circular_text": "x"}, cfg)
    final = resume_review(app, cfg, approved=True)
    assert calls == ["ingest"] and final["human_approval_status"] is True
