"""
Agentic Regulatory Sentinel — Entry Point

Demonstrates the full 4-node LangGraph pipeline with a sample SEBI circular.

Run:
    python main.py

Phase 1 runs automatically through:
  ingest_circular → audit_book → calculate_benefits → stage_dispatch
  … then PAUSES at human_review (LangGraph interrupt).

The script then simulates MFD review and resumes with an approval decision.
"""
import json
import os
from pathlib import Path
from dotenv import load_dotenv
from sentinel.graph import build_graph

# Load .env from the project root regardless of working directory
load_dotenv(Path(__file__).parent / ".env", override=True)

# ── Sample SEBI Circular (realistic demo text) ────────────────────────────────
SAMPLE_CIRCULAR = """\
SECURITIES AND EXCHANGE BOARD OF INDIA

Circular No.: SEBI/HO/IMD/IMD-II DOF3/P/CIR/2024/053
Date: March 15, 2024
Subject: Review of Total Expense Ratio (TER) for Small Cap and Mid Cap Mutual Fund Schemes
         and Mandatory Nomination Linkage

1. BACKGROUND
   SEBI had prescribed the framework for Total Expense Ratio (TER) for mutual fund schemes
   vide its circular dated September 18, 2018. Upon review of the expense structure and
   fund performance, SEBI has decided to revise TER caps for Small Cap and Mid Cap schemes.

2. REVISED TER CAPS
   a) Small Cap Funds: Maximum TER revised from 1.05% to 0.85% (Direct Plans) effective
      June 1, 2024.
   b) Mid Cap Funds: Maximum TER revised from 1.10% to 0.90% (Direct Plans) effective
      June 1, 2024.
   The reduction aims to pass on cost savings directly to investors.

3. MANDATORY NOMINATION LINKAGE
   In continuation of SEBI circular dated June 15, 2023, all folios without a registered
   nominee or an opt-out declaration must be linked by April 30, 2024. Folios not complying
   will be restricted to redemption-only mode until nomination is completed.

4. IMPACT ON DISTRIBUTORS
   Mutual Fund Distributors are advised to:
   a) Inform all clients holding Small Cap and Mid Cap fund units about the TER reduction
      and its expected positive impact on net returns.
   b) Immediately identify and contact all clients whose folios do not have a linked
      nominee and assist them in completing the nomination process before April 30, 2024.

5. APPLICABILITY
   This circular is applicable to all Asset Management Companies (AMCs) and Mutual Fund
   Distributors with immediate effect from the date of issuance, with the TER changes
   effective June 1, 2024.

For and on behalf of SEBI
(Madhabi Puri Buch)
Chairperson, SEBI
"""


def display_action_cards(action_cards: list, max_clients: int = 5) -> None:
    """Pretty-print the Action Cards for MFD review."""
    if not action_cards:
        print("\n[No Action Cards generated]")
        return

    for card in action_cards:
        print("\n" + "=" * 70)
        print("ACTION CARD")
        print("=" * 70)
        comm = card.get("commission_impact", {})
        print(f"Circular Reference : {card['circular_reference']}")
        print(f"Clients Affected   : {card['total_clients_affected']}")
        if comm.get("has_impact"):
            print(f"Commission Impact  : {comm['explanation'][:120]}")
            print(f"  [{comm.get('note', '')[:70]}]")
        else:
            print(f"Commission Impact  : {comm.get('explanation', 'No commission impact from this circular')}")
        print(f"\nVanilla Summary:\n{card['vanilla_summary']}\n")

        print(f"--- Sample Client Messages (showing {min(max_clients, len(card['clients']))} of {len(card['clients'])}) ---")
        for client in card["clients"][:max_clients]:
            tax = client.get("estimated_tax_impact", {})
            print(f"\n  Client : {client['client_name']} ({client['client_id']})")
            print(f"  Impact : {'; '.join(client['reasons_for_impact'][:1])[:120]}...")
            print(f"  Tax    : {tax.get('explanation', 'No tax implication')[:120]}")
            print(f"  NBA    : {client['next_best_action'][:120]}")
            print(f"\n  Draft Message:\n  {client['personalized_message'][:300]}...")
            print()


def main():
    print("=" * 70)
    print("  AGENTIC REGULATORY SENTINEL v1.0")
    print("  Tier-1 MFD Compliance Automation — Powered by LangGraph + Claude")
    print("=" * 70)

    # ── Build graph ──────────────────────────────────────────────────────────
    app = build_graph()
    config = {"configurable": {"thread_id": "circular-2024-053"}}

    # ── Phase 1: Run through to the human_review interrupt ───────────────────
    print("\n[Phase 1] Processing circular through all 4 modules...")
    print("  Module 1 → Jargon-Cutter (NLP + Translation)")
    print("  Module 2 → Book Auditor  (Portfolio Cross-Check)")
    print("  Module 3 → Benefit Engine (Tax & Commission Calc)")
    print("  Module 4 → Dispatcher    (Action Card Generation)")
    print()

    initial_state = {
        "raw_circular_text": SAMPLE_CIRCULAR,
        "circular_id": "",
        "vanilla_summary": "",
        "impact_triggers": [],
        "affected_clients": [],
        "mfd_commission_delta": 0.0,
        "action_cards": [],
        "human_approval_status": False,
        "processing_errors": [],
    }

    snapshot = app.invoke(initial_state, config)

    # ── Display Action Cards for MFD review ──────────────────────────────────
    print("\n" + "=" * 70)
    print("[Phase 1 Complete] — Graph paused at HUMAN REVIEW checkpoint")
    print("=" * 70)
    display_action_cards(snapshot.get("action_cards", []), max_clients=3)

    errors = snapshot.get("processing_errors", [])
    if errors:
        print(f"\n⚠ Processing errors: {errors}")

    # ── Simulate MFD decision ─────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("[Human Review] Simulating MFD approval...")
    decision = input("  Approve and dispatch messages? (y/n): ").strip().lower()
    approved = decision == "y"
    print(f"  MFD decision: {'✓ APPROVED' if approved else '✗ REVISION NEEDED'}")

    # ── Phase 2: Resume graph with approval decision ─────────────────────────
    print("\n[Phase 2] Resuming graph with approval decision...")
    final_state = app.invoke({"human_approval_status": approved}, config)

    if approved:
        cards = final_state.get("action_cards", [])
        total = len(cards[0].get("clients", [])) if cards else 0
        print(f"\n✓ Pipeline complete. {total} personalised client message(s) approved and ready to dispatch.")
    else:
        print("\n↺ Action Cards sent back to Dispatcher for revision.")

    # ── Optional: dump full state to JSON ────────────────────────────────────
    dump_path = "sentinel_output.json"
    with open(dump_path, "w", encoding="utf-8") as f:
        # Remove large raw fields for readability
        output = {k: v for k, v in final_state.items() if k != "raw_circular_text"}
        json.dump(output, f, indent=2, ensure_ascii=False, default=str)
    print(f"\n[Output] Full state written to: {dump_path}")


if __name__ == "__main__":
    main()
