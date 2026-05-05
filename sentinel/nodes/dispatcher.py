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
"""
import json
import os
from groq import Groq
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, List
from sentinel.state import GraphState

load_dotenv(Path(__file__).parents[2] / ".env", override=True)
_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
_MODEL = "llama-3.3-70b-versatile"

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


_BATCH_SIZE = 15  # clients per LLM call


def _build_client_brief(client: Dict) -> str:
    """One-line summary of a client for batch prompting."""
    holdings = client.get("affected_holdings", [])[:2]
    funds = ", ".join(h["fund_name"].split(" - ")[0] for h in holdings)
    tax_impact = client.get("estimated_tax_impact", {})
    tax_line = tax_impact.get("explanation", "No tax implication from this circular")
    nba = client.get("next_best_action", "")
    reason = client.get("reasons_for_impact", ["impacted by regulatory change"])[0][:120]
    return (
        f'ID:{client["client_id"]} | Name:{client["client_name"]} | '
        f'Funds:{funds} | TaxNote:{tax_line[:80]} | '
        f'Reason:{reason} | NextAction:{nba}'
    )


def _draft_batch(batch: List[Dict], vanilla_summary: str, circular_id: str) -> Dict[str, str]:
    """
    Draft messages for a batch of clients in a single LLM call.
    Returns {client_id: message}.
    """
    briefs = "\n".join(f"{i+1}. {_build_client_brief(c)}" for i, c in enumerate(batch))
    ids = [c["client_id"] for c in batch]

    prompt = (
        f"Circular: {circular_id}\n"
        f"Regulatory Change: {vanilla_summary}\n\n"
        f"Draft a personalised 3-paragraph client email for EACH of the {len(batch)} clients below.\n"
        f"Return ONLY a JSON object: {{\"CLIENT_ID\": \"message text\", ...}} — no other text.\n\n"
        f"Clients:\n{briefs}"
    )

    try:
        response = _client.chat.completions.create(
            model=_MODEL,
            messages=[
                {"role": "system", "content": _MSG_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            max_tokens=_BATCH_SIZE * 400,
        )
        raw = response.choices[0].message.content.strip()
        # Strip markdown fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        messages = json.loads(raw.strip())
        return {k: v for k, v in messages.items() if k in ids}
    except Exception as exc:
        # Fallback: template message for every client in the batch
        return {
            c["client_id"]: (
                f"Dear {c['client_name']},\n\n"
                f"A recent SEBI/AMFI circular ({circular_id}) affects your portfolio. "
                f"{c.get('next_best_action', 'Please contact us to discuss next steps.')}\n\n"
                f"Regards,\nYour MFD\n\n(Batch generation error: {exc})"
            )
            for c in batch
        }


def dispatcher_node(state: GraphState) -> dict:
    """
    LangGraph node: stage_dispatch
    Reads all state → writes action_cards with personalised messages.
    Batches clients into groups of {_BATCH_SIZE} per LLM call.
    """
    clients: List[Dict] = state.get("affected_clients", [])
    vanilla_summary: str = state.get("vanilla_summary", "")
    circular_id: str = state.get("circular_id", "UNKNOWN")
    commission_info: Dict = state.get("mfd_commission_delta", {})
    errors: List[str] = list(state.get("processing_errors", []))

    if not clients:
        return {"action_cards": [], "processing_errors": errors}

    # Build message map via batched LLM calls
    message_map: Dict[str, str] = {}
    batches = [clients[i:i + _BATCH_SIZE] for i in range(0, len(clients), _BATCH_SIZE)]
    for idx, batch in enumerate(batches):
        print(f"[Dispatcher] Drafting messages — batch {idx + 1}/{len(batches)} ({len(batch)} clients)")
        message_map.update(_draft_batch(batch, vanilla_summary, circular_id))

    client_cards = []
    for client in clients:
        cid = client["client_id"]
        message = message_map.get(cid, (
            f"Dear {client['client_name']},\n\n"
            f"A recent SEBI/AMFI circular ({circular_id}) affects your portfolio. "
            f"{client.get('next_best_action', 'Please contact us to discuss next steps.')}"
        ))
        client_cards.append({**client, "personalized_message": message})

    action_card = {
        "circular_reference": circular_id,
        "vanilla_summary": vanilla_summary,
        "total_clients_affected": len(client_cards),
        "commission_impact": commission_info,
        "clients": client_cards,
    }

    print(f"\n[Dispatcher] Action Card assembled: {len(client_cards)} client message(s) ready for review")

    return {
        "action_cards": [action_card],
        "affected_clients": client_cards,  # persist messages back to state
        "processing_errors": errors,
    }
