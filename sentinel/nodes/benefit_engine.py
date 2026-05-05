"""
Module 3 — The "Benefit & Reality" Engine (Circular-Driven)

DESIGN PRINCIPLE:
  Everything returned by this module is derived exclusively from the circular's
  impact_triggers. Tax implications are only surfaced if the circular directly
  or indirectly causes them. No hardcoded tax rates, no assumed implications.

Flow:
  1. Single LLM call  → analyze ALL triggers: does this circular cause tax
                         events? what does it actually say about commissions?
  2. Pure Python loop → apply that analysis to each affected client — no more
                         LLM calls regardless of client count.
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

_ANALYSIS_SYSTEM = """\
You are a fiduciary regulatory compliance analyst specialising in Indian mutual fund regulations (SEBI/AMFI).

You will be given impact triggers extracted from a regulatory circular. For each trigger you must determine:
1. Whether it causes TAX implications for investors — directly (e.g. forced redemption/switch) or indirectly
   (e.g. fund reclassification that changes the tax treatment of existing holdings).
2. What the MFD commission/revenue impact is — using ONLY numbers explicitly stated in the circular.
3. What the correct client action is — specific to THIS trigger's change.

STRICT RULES:
- A TER reduction does NOT cause a tax event. It lowers ongoing costs. Do not invent tax implications.
- A nomination/KYC mandate is administrative. It has NO tax implication.
- A forced fund merger, mandatory switch, or category reclassification CAN cause LTCG/STCG events
  because the investor is forced to exit existing units — flag this as a tax implication.
- For commission impact: use ONLY the actual percentages or figures stated in the circular.
  If the circular says "TER reduced from 1.05% to 0.85%", use those numbers.
  If no specific figure is mentioned, say so explicitly — do not estimate or assume.
- client_action must be specific to the regulatory change in this trigger, not generic.
"""


def _analyze_circular_for_impacts(triggers: List[Dict], vanilla_summary: str) -> Dict:
    """
    Single LLM call — analyze every trigger for tax and commission relevance.

    Returns a dict keyed by mandate_id:
    {
      "T001": {
        "has_tax_implication": false,
        "tax_explanation": "...",
        "has_commission_impact": true,
        "commission_explanation": "TER reduced from 1.05% to 0.85% for Small Cap...",
        "client_action": "...",
        "urgency": "MEDIUM"
      },
      ...
    }
    """
    prompt = f"""Circular Summary: {vanilla_summary}

Impact Triggers from this circular:
{json.dumps(triggers, indent=2)}

For EACH trigger, return a JSON object with this exact structure:
{{
  "MANDATE_ID": {{
    "has_tax_implication": true or false,
    "tax_explanation": "Why this trigger does or does not cause a tax event for investors. If yes, specify what type (capital gains on forced exit, change in tax treatment, etc.) and under what conditions.",
    "has_commission_impact": true or false,
    "commission_explanation": "Use ONLY numbers from the circular. State the actual change. If no numbers are given, write: 'Circular does not specify exact figures.'",
    "client_action": "Specific 1-2 sentence action for clients impacted by THIS trigger.",
    "urgency": "LOW, MEDIUM, HIGH, or CRITICAL"
  }}
}}

Return ONLY valid JSON. No markdown fences, no extra text."""

    try:
        response = _client.chat.completions.create(
            model=_MODEL,
            messages=[
                {"role": "system", "content": _ANALYSIS_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            max_tokens=1500,
        )
        raw = response.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw.strip())

    except Exception as exc:
        return {
            t.get("mandate_id", f"T{i}"): {
                "has_tax_implication": False,
                "tax_explanation": f"Analysis failed — manual review required. ({exc})",
                "has_commission_impact": False,
                "commission_explanation": "Analysis failed — manual review required.",
                "client_action": "Please contact your distributor for guidance on this change.",
                "urgency": "MEDIUM",
            }
            for i, t in enumerate(triggers)
        }


def _build_client_impact(client: Dict, trigger_analysis: Dict) -> Dict:
    """
    Apply the trigger analysis to a single client — pure Python, no LLM.
    Only surfaces tax or commission information if the circular actually causes it.
    """
    triggered_by = client.get("triggers_hit", [])
    relevant = {mid: trigger_analysis[mid] for mid in triggered_by if mid in trigger_analysis}

    # ── Tax impact ────────────────────────────────────────────────────────────
    tax_relevant = {mid: a for mid, a in relevant.items() if a.get("has_tax_implication")}

    if tax_relevant:
        explanations = [f"[{mid}] {a['tax_explanation']}" for mid, a in tax_relevant.items()]
        tax_impact = {
            "has_tax_implication": True,
            "explanation": " | ".join(explanations),
        }
    else:
        tax_impact = {
            "has_tax_implication": False,
            "explanation": "This circular does not cause a direct or indirect tax event for your holdings.",
        }

    # ── Next Best Action — one per unique trigger, deduped ───────────────────
    seen: set = set()
    actions: List[str] = []
    for a in relevant.values():
        action = a.get("client_action", "")
        if action and action not in seen:
            seen.add(action)
            actions.append(action)

    next_best_action = " ".join(actions) if actions else (
        "No immediate action required. We will monitor this circular and contact you if needed."
    )

    # ── Urgency = highest across all triggered mandates ───────────────────────
    rank = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
    urgency = max(
        (a.get("urgency", "LOW") for a in relevant.values()),
        key=lambda u: rank.get(u, 0),
        default="LOW",
    )

    return {**client, "estimated_tax_impact": tax_impact, "next_best_action": next_best_action, "urgency": urgency}


def _build_commission_summary(trigger_analysis: Dict) -> Dict:
    """
    Commission impact derived solely from what the circular states.
    No hardcoded TER proxies or trail share assumptions.
    """
    commission_notes = [
        f"[{mid}] {a['commission_explanation']}"
        for mid, a in trigger_analysis.items()
        if a.get("has_commission_impact")
    ]

    if not commission_notes:
        return {
            "has_impact": False,
            "explanation": "This circular does not directly affect MFD trail commissions.",
        }

    return {
        "has_impact": True,
        "explanation": " | ".join(commission_notes),
        "note": (
            "INFORMATIONAL ONLY. Exact INR impact depends on your AUM breakdown per fund. "
            "No portfolio changes should be made to offset this."
        ),
    }


def benefit_engine_node(state: GraphState) -> dict:
    """
    LangGraph node: calculate_benefits

    1 LLM call to analyze triggers → pure Python to apply per client.
    """
    triggers: List[Dict] = state.get("impact_triggers", [])
    clients: List[Dict] = state.get("affected_clients", [])
    vanilla_summary: str = state.get("vanilla_summary", "")
    errors: List[str] = list(state.get("processing_errors", []))

    if not clients:
        return {"affected_clients": [], "mfd_commission_delta": {}, "processing_errors": errors}

    print(f"\n[Benefit Engine] Analyzing {len(triggers)} trigger(s) against the circular...")
    trigger_analysis = _analyze_circular_for_impacts(triggers, vanilla_summary)

    tax_triggers = [mid for mid, a in trigger_analysis.items() if a.get("has_tax_implication")]
    comm_triggers = [mid for mid, a in trigger_analysis.items() if a.get("has_commission_impact")]
    print(f"[Benefit Engine] Tax-relevant triggers   : {tax_triggers if tax_triggers else 'None'}")
    print(f"[Benefit Engine] Commission-relevant     : {comm_triggers if comm_triggers else 'None'}")

    enriched = [_build_client_impact(c, trigger_analysis) for c in clients]
    commission_info = _build_commission_summary(trigger_analysis)

    print(f"[Benefit Engine] Processed {len(enriched)} client(s)")

    return {
        "affected_clients": enriched,
        "mfd_commission_delta": commission_info,
        "processing_errors": errors,
    }
