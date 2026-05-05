"""
LangGraph State Machine — Regulatory Sentinel

Graph topology:
  START
    → ingest_circular   (Module 1: Jargon-Cutter)
    → audit_book        (Module 2: Book Auditor)
    → calculate_benefits(Module 3: Benefit Engine)
    → stage_dispatch    (Module 4: Dispatcher)
    → human_review      ── interrupt_before ──┐
        ├─ approved  → END                    │
        └─ rejected  → stage_dispatch ────────┘

The graph is compiled with a MemorySaver checkpointer so state is persisted
across the human-review interrupt.  Pass `interrupt_before=["human_review"]`
to pause and resume after MFD approval.
"""
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from sentinel.state import GraphState
from sentinel.nodes.jargon_cutter import jargon_cutter_node
from sentinel.nodes.book_auditor import book_auditor_node
from sentinel.nodes.benefit_engine import benefit_engine_node
from sentinel.nodes.dispatcher import dispatcher_node


# ── Human-in-the-Loop node ───────────────────────────────────────────────────

def human_review_node(state: GraphState) -> dict:
    """
    Pause point for MFD review.

    This node is declared but the graph is compiled with
    `interrupt_before=["human_review"]`, so LangGraph halts execution here
    and returns control to the caller.

    To resume, invoke the graph again on the same thread_id with:
        {"human_approval_status": True}   # approved
        {"human_approval_status": False}  # revision needed → loops back to Dispatcher
    """
    # When resumed, human_approval_status is already in state (set by the caller).
    # Nothing to compute here — just pass through.
    return {}


# ── Conditional routing ──────────────────────────────────────────────────────

def _route_after_review(state: GraphState) -> str:
    if state.get("human_approval_status", False):
        return "approved"
    return "revision_needed"


# ── Graph factory ─────────────────────────────────────────────────────────────

def build_graph(checkpointer=None):
    """
    Compile and return the Regulatory Sentinel LangGraph application.

    Args:
        checkpointer: A LangGraph checkpointer for state persistence.
                      Defaults to an in-memory MemorySaver.

    Returns:
        A compiled LangGraph app ready for `.invoke()` / `.stream()`.

    Usage:
        app = build_graph()
        config = {"configurable": {"thread_id": "run-001"}}

        # Phase 1: run through to the human_review interrupt
        snapshot = app.invoke({"raw_circular_text": circular_text}, config)

        # … MFD reviews snapshot["action_cards"] …

        # Phase 2: resume with approval decision
        final = app.invoke({"human_approval_status": True}, config)
    """
    graph = StateGraph(GraphState)

    # Register nodes
    graph.add_node("ingest_circular", jargon_cutter_node)
    graph.add_node("audit_book", book_auditor_node)
    graph.add_node("calculate_benefits", benefit_engine_node)
    graph.add_node("stage_dispatch", dispatcher_node)
    graph.add_node("human_review", human_review_node)

    # Linear pipeline edges
    graph.add_edge(START, "ingest_circular")
    graph.add_edge("ingest_circular", "audit_book")
    graph.add_edge("audit_book", "calculate_benefits")
    graph.add_edge("calculate_benefits", "stage_dispatch")
    graph.add_edge("stage_dispatch", "human_review")

    # Conditional edge: approved → END, revision → back to Dispatcher
    graph.add_conditional_edges(
        "human_review",
        _route_after_review,
        {
            "approved": END,
            "revision_needed": "stage_dispatch",
        },
    )

    cp = checkpointer if checkpointer is not None else MemorySaver()

    return graph.compile(
        checkpointer=cp,
        interrupt_before=["human_review"],
    )
