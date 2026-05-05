"""
Module 1 — The "Jargon-Cutter"
NLP Ingestion & Translation Node

Responsibilities:
  1. Parse dense SEBI/AMFI circular text.
  2. Produce a plain-English "Vanilla Summary" suitable for client-facing communication.
  3. Extract a structured list of "Impact Triggers" (JSON) for downstream processing.
"""
import json
import os
import re
from pathlib import Path
from groq import Groq
from dotenv import load_dotenv
from sentinel.state import GraphState

load_dotenv(Path(__file__).parents[2] / ".env", override=True)
_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
_MODEL = "llama-3.3-70b-versatile"

_SYSTEM_PROMPT = """\
You are a senior regulatory compliance analyst specialising in Indian mutual fund regulations (SEBI/AMFI).

Your task is to process regulatory circulars and return two things:

1. VANILLA_SUMMARY — 3-5 plain-English sentences a non-expert MFD can read and safely forward to clients.
   - No legal jargon.
   - Lead with what is changing and why it matters.
   - Mention the effective date / deadline if present.

2. IMPACT_TRIGGERS_JSON — A JSON object strictly following this schema:
{
  "circular_id": "string",
  "circular_date": "YYYY-MM-DD or null",
  "effective_date": "YYYY-MM-DD or null",
  "deadline": "YYYY-MM-DD or null",
  "triggers": [
    {
      "mandate_id": "T001",
      "rule_change": "One-sentence description of the rule change",
      "fund_categories_impacted": ["Small Cap", "Mid Cap", ...],
      "asset_classes_impacted": ["Equity", "Debt", "Hybrid", "Gold", "International"],
      "compliance_requirements": ["Action distributor must take"],
      "severity": "LOW | MEDIUM | HIGH | CRITICAL",
      "client_filter": {
        "type": "category_holding | no_nomination | kyc_pending | all",
        "categories": ["Small Cap"]
      }
    }
  ]
}

Allowed values for client_filter.type:
  "category_holding" — clients holding funds in listed categories
  "no_nomination"    — clients without linked nominees
  "kyc_pending"      — clients with incomplete KYC
  "all"              — all clients

Rules:
- Output ONLY valid JSON for IMPACT_TRIGGERS_JSON. No markdown fences, no extra text.
- If a date is absent, use null (not empty string).
- Be exhaustive — extract every distinct regulatory change as a separate trigger.\
"""


def _parse_llm_response(raw: str) -> tuple[str, dict]:
    """Split LLM output into (vanilla_summary, impact_triggers_dict)."""
    vanilla_summary = ""
    impact_triggers = {}

    if "VANILLA_SUMMARY" in raw and "IMPACT_TRIGGERS_JSON" in raw:
        parts = raw.split("IMPACT_TRIGGERS_JSON", 1)
        vanilla_part = parts[0].replace("VANILLA_SUMMARY", "").strip(" :\n")
        json_part = parts[1].strip(" :\n")

        vanilla_summary = vanilla_part

        # Strip markdown fences if present
        json_part = re.sub(r"^```(?:json)?\s*", "", json_part, flags=re.MULTILINE)
        json_part = re.sub(r"\s*```$", "", json_part, flags=re.MULTILINE)

        try:
            impact_triggers = json.loads(json_part.strip())
        except json.JSONDecodeError as exc:
            impact_triggers = {
                "error": f"JSON parse failed: {exc}",
                "circular_id": "PARSE_ERROR",
                "triggers": [],
            }
    else:
        # Fallback: treat entire response as vanilla summary
        vanilla_summary = raw.strip()
        impact_triggers = {"circular_id": "UNKNOWN", "triggers": []}

    return vanilla_summary, impact_triggers


def jargon_cutter_node(state: GraphState) -> dict:
    """
    LangGraph node: ingest_circular
    Reads raw_circular_text → writes vanilla_summary, impact_triggers, circular_id.
    """
    raw_text = state.get("raw_circular_text", "")
    errors: list[str] = list(state.get("processing_errors", []))

    if not raw_text.strip():
        errors.append("jargon_cutter: raw_circular_text is empty")
        return {
            "vanilla_summary": "",
            "impact_triggers": [],
            "circular_id": "EMPTY",
            "processing_errors": errors,
        }

    prompt = (
        f"Process the following SEBI/AMFI circular.\n\n"
        f"Circular Text:\n---\n{raw_text}\n---\n\n"
        f"VANILLA_SUMMARY\n[Write plain-English summary here]\n\n"
        f"IMPACT_TRIGGERS_JSON\n[Write the JSON here]"
    )

    try:
        response = _client.chat.completions.create(
            model=_MODEL,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            max_tokens=2048,
        )
        raw_output = response.choices[0].message.content
    except Exception as exc:
        errors.append(f"jargon_cutter LLM error: {exc}")
        return {
            "vanilla_summary": "",
            "impact_triggers": [],
            "circular_id": "LLM_ERROR",
            "processing_errors": errors,
        }

    vanilla_summary, triggers_dict = _parse_llm_response(raw_output)

    # Normalise: impact_triggers stored as list of trigger dicts
    raw_triggers = triggers_dict.get("triggers", [])
    circular_id = triggers_dict.get("circular_id", "UNKNOWN")

    # Attach top-level dates to each trigger for convenience
    for t in raw_triggers:
        t.setdefault("effective_date", triggers_dict.get("effective_date"))
        t.setdefault("deadline", triggers_dict.get("deadline"))
        t.setdefault("circular_date", triggers_dict.get("circular_date"))

    print(f"\n[Jargon-Cutter] Circular ID: {circular_id}")
    print(f"[Jargon-Cutter] Extracted {len(raw_triggers)} impact trigger(s)")
    print(f"[Jargon-Cutter] Vanilla Summary:\n  {vanilla_summary[:200]}...")

    return {
        "vanilla_summary": vanilla_summary,
        "impact_triggers": raw_triggers,
        "circular_id": circular_id,
        "processing_errors": errors,
    }
