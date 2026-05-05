"""
GraphState — Central state schema for the Regulatory Sentinel.

All nodes read from and write to this shared state object.
LangGraph merges partial dicts returned by each node into the running state.
"""
from typing import Any, Dict, List, Optional
from typing_extensions import TypedDict


class GraphState(TypedDict):
    # ── Module 1: Jargon-Cutter ──────────────────────────────────────────────
    raw_circular_text: str           # Raw SEBI/AMFI circular text (input)
    circular_id: str                 # e.g. "SEBI/HO/IMD/2024/001"
    vanilla_summary: str             # Plain-English translation for clients
    impact_triggers: List[Dict]      # Structured list of regulatory impact triggers

    # ── Module 2: Book Auditor ───────────────────────────────────────────────
    # Each dict contains:
    #   client_id, client_name, email, phone, pan, risk_profile, tax_bracket_pct,
    #   affected_holdings: List[dict], reason_for_impact: str,
    #   portfolio_exposure_pct: float
    affected_clients: List[Dict]

    # ── Module 3: Benefit & Reality Engine ───────────────────────────────────
    # mfd_commission_delta is PURELY INFORMATIONAL.
    # Derived from what the circular actually states — no hardcoded assumptions.
    # Shape: {"has_impact": bool, "explanation": str, "note": str (optional)}
    mfd_commission_delta: Dict       # circular-derived commission impact summary

    # ── Module 4: Dispatcher ─────────────────────────────────────────────────
    # Each Action Card dict:
    #   circular_reference, vanilla_summary, total_clients_affected,
    #   estimated_commission_delta, clients: List[dict with personalized_message]
    action_cards: List[Dict]

    # ── Human-in-the-Loop ────────────────────────────────────────────────────
    human_approval_status: bool      # True = approved, False = needs revision

    # ── Diagnostics ──────────────────────────────────────────────────────────
    processing_errors: List[str]
