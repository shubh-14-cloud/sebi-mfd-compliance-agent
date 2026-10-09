"""
Module 4 — The "Ready-to-Act" Dispatcher

Responsibilities:
  - Stage the final output for the Human-in-the-Loop (the MFD).
  - Generate pre-drafted, highly personalised client messages.
  - Assemble "Action Cards" — the dashboard payload the MFD reviews and approves.

Each Action Card contains:
  1. The "Vanilla Terms" explanation of the rule.
  2. The list of specifically impacted clients.
  3. The estimated commission impact (informational).
  4. A pre-drafted, personalised message for each impacted client.

If the MFD rejects a draft, their feedback (state["reviewer_feedback"]) is
included in the prompt when this node re-runs.
"""
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List
from mock_data.portfolio_db import db
from sentinel.llm_utils import generate_json
from sentinel.state import GraphState

_MSG_SYSTEM = """\
You are a trusted financial advisor drafting a client communication on behalf of a SEBI-registered
Mutual Fund Distributor (MFD).

Guidelines:
- Tone: warm, professional, reassuring — never alarming.
- Lead with what is changing and how it specifically affects THIS client.
- Include the client's actual fund name and approximate exposure amount.
- State the recommended action (next_best_action) clearly.
- End with an invitation to connect for questions.
- Length: 3-5 short paragraphs.
- Never mention commissions or distributor earnings.
- Never suggest switching funds to avoid the regulation.
- Write in clear, simple English — avoid financial jargon.
"""


_BATCH_SIZE = 25   # clients per LLM call (fewer calls = friendlier to API rate limits)
_MAX_WORKERS = 4   # concurrent LLM calls
# Messages are drafted only for the most affected clients (highest urgency, then exposure).
# The Action Card still reports the true total. Set MAX_DRAFT_CLIENTS to change the cap.
_MAX_DRAFT_CLIENTS = max(1, int(os.environ.get("MAX_DRAFT_CLIENTS", "10")))
_URGENCY_RANK = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}


def _build_client_brief(client: Dict) -> str:
    """One-line summary of a client for batch prompting."""
    holdings = client.get("affected_holdings", [])[:2]
    funds = ", ".join(h["fund_name"].split(" - ")[0] for h in holdings)
    tax_impact = client.get("estimated_tax_impact", {})
    tax_line = tax_impact.get("explanation", "No tax implication from this circular")
    nba = client.get("next_best_action", "")
    reasons = client.get("reasons_for_impact") or ["impacted by regulatory change"]
    reason = reasons[0][:120]
    return (
        f'ID:{client["client_id"]} | Name:{client["client_name"]} | '
        f'Funds:{funds} | TaxNote:{tax_line[:80]} | '
        f'Reason:{reason} | NextAction:{nba}'
    )


def _template_message(client: Dict, circular_id: str, demo: bool) -> str:
    """Plain fallback used when the model is unavailable. Never claims impact on a demo client."""
    if demo:
        body = (
            f"We reviewed the recent SEBI circular ({circular_id}). It does not affect your "
            f"investments, and no action is needed from you."
        )
    else:
        body = (
            f"A recent SEBI/AMFI circular ({circular_id}) affects your portfolio. "
            f"{client.get('next_best_action', 'Please contact us to discuss next steps.')}"
        )
    return f"Dear {client['client_name']},\n\n{body}\n\nRegards,\nYour MFD"


def _draft_batch(batch: List[Dict], vanilla_summary: str, circular_id: str, feedback: str = "", demo: bool = False):
    """
    Draft messages for a batch of clients in a single LLM call.
    Returns ({client_id: message}, error_or_None).
    """
    briefs = "\n".join(f"{i+1}. {_build_client_brief(c)}" for i, c in enumerate(batch))
    ids = [c["client_id"] for c in batch]

    feedback_block = (
        f"\nThe MFD rejected the previous draft with this feedback — address it:\n{feedback}\n"
        if feedback.strip() else ""
    )
    task = (
        f"This circular does NOT require any action from these clients. Draft a short, reassuring "
        f"2-paragraph informational note for EACH of the {len(batch)} clients below, saying so. "
        f"Do not claim they are impacted.\n"
        if demo else
        f"Draft a personalised 3-paragraph client email for EACH of the {len(batch)} clients below.\n"
    )
    prompt = (
        f"Circular: {circular_id}\n"
        f"Regulatory Change: {vanilla_summary}\n"
        f"{feedback_block}\n"
        f"{task}"
        f"Return ONLY a JSON object: {{\"CLIENT_ID\": \"message text\", ...}} — no other text.\n\n"
        f"Clients:\n{briefs}"
    )

    def _validate(data):
        if not isinstance(data, dict):
            raise ValueError("expected a JSON object mapping client_id -> message")
        return data

    try:
        messages = generate_json(_MSG_SYSTEM, prompt, validate=_validate)
        return {k: v for k, v in messages.items() if k in ids and isinstance(v, str)}, None
    except Exception as exc:
        # Fallback: template message for every client in the batch.
        # The error is reported via processing_errors, never inside the client's message.
        fallback = {c["client_id"]: _template_message(c, circular_id, demo) for c in batch}
        return fallback, str(exc)[:200]


def dispatcher_node(state: GraphState) -> dict:
    """
    LangGraph node: stage_dispatch
    Reads all state → writes action_cards with personalised messages.
    Batches clients into groups of {_BATCH_SIZE} per LLM call, run concurrently.
    """
    clients: List[Dict] = state.get("affected_clients", [])
    vanilla_summary: str = state.get("vanilla_summary", "")
    circular_id: str = state.get("circular_id", "UNKNOWN")
    commission_info: Dict = state.get("mfd_commission_delta", {})
    feedback: str = state.get("reviewer_feedback", "")
    errors: List[str] = list(state.get("processing_errors", []))

    all_clients = clients  # full affected list; kept in state so redrafts still know the true total
    total_affected = len(clients)
    demo = False

    if not clients:
        if not vanilla_summary:
            return {"action_cards": [], "processing_errors": errors}
        # Nobody is affected: show a clearly-labelled DEMO of the output for a few sample clients
        demo = True
        clients = [
            {
                "client_id": c["client_id"],
                "client_name": c["name"],
                "affected_holdings": c["holdings"][:2],
                "reasons_for_impact": ["DEMO ONLY: this circular does not affect this client."],
                "estimated_tax_impact": {"has_tax_implication": False,
                                         "explanation": "This circular does not cause a tax event."},
                "next_best_action": "No action needed.",
                "triggers_hit": [],
            }
            for c in db.get_all_clients()[:_MAX_DRAFT_CLIENTS]
        ]
    elif len(clients) > _MAX_DRAFT_CLIENTS:
        # Draft only for the most affected clients
        clients = sorted(
            clients,
            key=lambda c: (_URGENCY_RANK.get(c.get("urgency", "LOW"), 0), c.get("portfolio_exposure_pct", 0)),
            reverse=True,
        )[:_MAX_DRAFT_CLIENTS]

    batches = [clients[i:i + _BATCH_SIZE] for i in range(0, len(clients), _BATCH_SIZE)]
    print(f"[Dispatcher] Drafting messages for {len(clients)} of {total_affected} affected client(s) — "
          f"{len(batches)} batch(es)" + (" (DEMO)" if demo else "")
          + (" (with MFD feedback)" if feedback.strip() else ""))

    message_map: Dict[str, str] = {}
    failed_batches, last_error = 0, ""
    with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as pool:
        for result, err in pool.map(lambda b: _draft_batch(b, vanilla_summary, circular_id, feedback, demo), batches):
            message_map.update(result)
            if err:
                failed_batches += 1
                last_error = err
    if failed_batches:
        errors.append(
            f"dispatcher: {failed_batches}/{len(batches)} batch(es) fell back to template messages "
            f"(last error: {last_error})"
        )

    client_cards = []
    for client in clients:
        cid = client["client_id"]
        message = message_map.get(cid) or _template_message(client, circular_id, demo)
        client_cards.append({**client, "personalized_message": message})

    action_card = {
        "circular_reference": circular_id,
        "vanilla_summary": vanilla_summary,
        "total_clients_affected": total_affected,  # true count, even if fewer are shown
        "clients_shown": len(client_cards),
        "demo": demo,
        "commission_impact": commission_info,
        "clients": client_cards,
    }

    print(f"\n[Dispatcher] Action Card assembled: {len(client_cards)} message(s) ready for review"
          + (" (DEMO — nobody is affected)" if demo else ""))

    return {
        "action_cards": [action_card],
        # Keep every affected client in state (drafted ones carry their message); demo clients aren't "affected"
        "affected_clients": [] if demo else [
            {c["client_id"]: c for c in client_cards}.get(a["client_id"], a) for a in all_clients
        ],
        "processing_errors": errors,
    }
