"""
Module 1 — The "Jargon-Cutter"
NLP Ingestion & Translation Node

Responsibilities:
  1. Parse dense SEBI/AMFI circular text.
  2. Produce a plain-English "Vanilla Summary" suitable for client-facing communication.
  3. Extract a structured list of "Impact Triggers" (JSON) for downstream processing.

The LLM is called in JSON mode and its output is validated with Pydantic, so
malformed or off-schema responses are retried instead of silently mis-parsed.
"""
from typing import List, Literal, Optional
from pydantic import BaseModel, Field

from sentinel.llm_utils import generate_json
from sentinel.state import GraphState

_SYSTEM_PROMPT = """\
You are a senior regulatory compliance analyst specialising in Indian mutual fund regulations (SEBI/AMFI).

Process the regulatory circular and return ONE JSON object with this schema:
{
  "vanilla_summary": "3-5 plain-English sentences a non-expert MFD can safely forward to clients. No legal jargon. Lead with what is changing and why it matters. Mention the effective date / deadline if present.",
  "circular_id": "string",
  "circular_date": "YYYY-MM-DD or null",
  "effective_date": "YYYY-MM-DD or null",
  "deadline": "YYYY-MM-DD or null",
  "triggers": [
    {
      "mandate_id": "T001",
      "rule_change": "One-sentence description of the rule change",
      "fund_categories_impacted": ["Small Cap", "Mid Cap"],
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
- Output ONLY the JSON object.
- If a date is absent, use null (not empty string).
- Be exhaustive — extract every distinct regulatory change as a separate trigger.\
"""


class ClientFilter(BaseModel):
    type: Literal["category_holding", "no_nomination", "kyc_pending", "all"] = "all"
    categories: List[str] = Field(default_factory=list)


class Trigger(BaseModel):
    mandate_id: str
    rule_change: str
    fund_categories_impacted: List[str] = Field(default_factory=list)
    asset_classes_impacted: List[str] = Field(default_factory=list)
    compliance_requirements: List[str] = Field(default_factory=list)
    severity: str = "MEDIUM"
    client_filter: ClientFilter = Field(default_factory=ClientFilter)


class CircularAnalysis(BaseModel):
    vanilla_summary: str
    circular_id: str = "UNKNOWN"
    circular_date: Optional[str] = None
    effective_date: Optional[str] = None
    deadline: Optional[str] = None
    triggers: List[Trigger] = Field(default_factory=list)


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

    prompt = f"Process the following SEBI/AMFI circular.\n\nCircular Text:\n---\n{raw_text}\n---"

    try:
        analysis = generate_json(_SYSTEM_PROMPT, prompt, validate=CircularAnalysis.model_validate)
    except Exception as exc:
        errors.append(f"jargon_cutter LLM/validation error: {exc}")
        return {
            "vanilla_summary": "",
            "impact_triggers": [],
            "circular_id": "LLM_ERROR",
            "processing_errors": errors,
        }

    # Attach top-level dates to each trigger so downstream nodes don't need the parent object
    triggers = []
    for t in analysis.triggers:
        d = t.model_dump()
        d["effective_date"] = analysis.effective_date
        d["deadline"] = analysis.deadline
        d["circular_date"] = analysis.circular_date
        triggers.append(d)

    print(f"\n[Jargon-Cutter] Circular ID: {analysis.circular_id}")
    print(f"[Jargon-Cutter] Extracted {len(triggers)} impact trigger(s)")
    print(f"[Jargon-Cutter] Vanilla Summary:\n  {analysis.vanilla_summary[:200]}...")

    return {
        "vanilla_summary": analysis.vanilla_summary,
        "impact_triggers": triggers,
        "circular_id": analysis.circular_id,
        "processing_errors": errors,
    }
