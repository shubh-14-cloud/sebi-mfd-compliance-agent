"""
Module 2 — The "Autonomous Book Auditor"
Cross-Check Logic Node

Responsibilities:
  1. Take the structured Impact Triggers from Module 1.
  2. Autonomously query the mock MFD database (650+ portfolios).
  3. Identify every client affected by each trigger.
  4. Generate a personalised "Reason for Impact" per client based on their actual holdings.
"""
from typing import Dict, List
from mock_data.portfolio_db import db
from sentinel.state import GraphState


def _get_clients_for_trigger(trigger: Dict) -> List[Dict]:
    """Return the subset of clients matched by a trigger's client_filter."""
    cf = trigger.get("client_filter", {})
    filter_type = cf.get("type", "all")

    if filter_type == "category_holding":
        categories = cf.get("categories", [])
        return db.get_clients_by_categories(categories)

    if filter_type == "no_nomination":
        return db.get_clients_without_nomination()

    if filter_type == "kyc_pending":
        return db.get_clients_with_pending_kyc()

    # "all" or unknown — every client
    return db.get_all_clients()


def _build_affected_holdings(client: Dict, trigger: Dict) -> List[Dict]:
    """Return only the holdings relevant to this trigger."""
    cf = trigger.get("client_filter", {})
    filter_type = cf.get("type", "all")
    target_categories = set(cf.get("categories", []))

    if filter_type == "category_holding" and target_categories:
        return [h for h in client["holdings"] if h["category"] in target_categories]

    return client["holdings"]


def _portfolio_exposure_pct(affected_holdings: List[Dict], total_value: float) -> float:
    """What percentage of the client's portfolio is in the impacted funds."""
    if total_value == 0:
        return 0.0
    affected_value = sum(h["current_value"] for h in affected_holdings)
    return round((affected_value / total_value) * 100, 1)


def _build_reason_for_impact(client: Dict, trigger: Dict, affected_holdings: List[Dict], exposure_pct: float) -> str:
    """
    Generate a personalised reason string without an LLM call —
    keeps this node fast and deterministic.
    """
    rule = trigger.get("rule_change", "regulatory change")
    fund_names = [h["fund_name"].split(" - ")[0] for h in affected_holdings[:3]]
    funds_str = ", ".join(fund_names)
    if len(affected_holdings) > 3:
        funds_str += f" and {len(affected_holdings) - 3} more"

    cf_type = trigger.get("client_filter", {}).get("type", "all")

    if cf_type == "no_nomination":
        return (
            f"Your account does not have a linked nominee. SEBI now mandates nomination "
            f"linkage — you must complete this by the deadline to avoid account freeze."
        )

    if cf_type == "kyc_pending":
        return (
            f"Your KYC is incomplete. Under the new SEBI directive your transactions may "
            f"be restricted until full KYC verification is done."
        )

    return (
        f"You are impacted because {exposure_pct}% of your portfolio (₹"
        f"{sum(h['current_value'] for h in affected_holdings):,.0f}) is invested in "
        f"{funds_str}, which fall under the '{', '.join(trigger.get('fund_categories_impacted', ['affected']))}' "
        f"category. The new rule: {rule}."
    )


def book_auditor_node(state: GraphState) -> dict:
    """
    LangGraph node: audit_book
    Reads impact_triggers → writes affected_clients.
    """
    triggers: List[Dict] = state.get("impact_triggers", [])
    errors: List[str] = list(state.get("processing_errors", []))

    if not triggers:
        errors.append("book_auditor: no impact_triggers to process")
        return {"affected_clients": [], "processing_errors": errors}

    # Deduplicate clients across multiple triggers;
    # a client may be hit by more than one trigger.
    client_map: Dict[str, Dict] = {}  # client_id → enriched record

    for trigger in triggers:
        matched_clients = _get_clients_for_trigger(trigger)

        for client in matched_clients:
            cid = client["client_id"]
            affected_holdings = _build_affected_holdings(client, trigger)

            if not affected_holdings:
                continue

            exposure_pct = _portfolio_exposure_pct(
                affected_holdings, client["total_portfolio_value"]
            )
            reason = _build_reason_for_impact(client, trigger, affected_holdings, exposure_pct)

            if cid not in client_map:
                client_map[cid] = {
                    "client_id": cid,
                    "client_name": client["name"],
                    "email": client["email"],
                    "phone": client["phone"],
                    "pan": client["pan"],
                    "risk_profile": client["risk_profile"],
                    "tax_bracket_pct": client["tax_bracket_pct"],
                    "kyc_status": client["kyc_status"],
                    "nomination_linked": client["nomination_linked"],
                    "total_portfolio_value": client["total_portfolio_value"],
                    "affected_holdings": [],
                    "triggers_hit": [],
                    "reasons_for_impact": [],
                    "portfolio_exposure_pct": 0.0,
                    # Populated by benefit_engine
                    "estimated_tax_impact": {},
                    "next_best_action": "",
                    "personalized_message": "",
                }

            record = client_map[cid]
            record["affected_holdings"].extend(affected_holdings)
            record["triggers_hit"].append(trigger.get("mandate_id", "?"))
            record["reasons_for_impact"].append(reason)

            # Recompute exposure including new holdings
            unique_holdings = {h["isin"]: h for h in record["affected_holdings"]}.values()
            record["affected_holdings"] = list(unique_holdings)
            record["portfolio_exposure_pct"] = _portfolio_exposure_pct(
                record["affected_holdings"], client["total_portfolio_value"]
            )

    affected_clients = list(client_map.values())

    print(f"\n[Book Auditor] Scanned {db.get_summary_stats()['total_clients']} client portfolios")
    print(f"[Book Auditor] Found {len(affected_clients)} affected client(s) across {len(triggers)} trigger(s)")

    return {"affected_clients": affected_clients, "processing_errors": errors}
