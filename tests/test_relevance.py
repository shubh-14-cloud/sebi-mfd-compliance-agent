"""Irrelevant circulars must not produce 'You are impacted' messages (LLM stubbed)."""
import sentinel.nodes.jargon_cutter as jc
import sentinel.nodes.benefit_engine as be
import sentinel.nodes.dispatcher as dp
from sentinel.graph import build_graph


def _run(fake):
    for m in (jc, be, dp):
        m.generate_json = fake
    app = build_graph()
    return app.invoke({"raw_circular_text": "x", "processing_errors": []},
                      {"configurable": {"thread_id": "t"}})


def test_irrelevant_circular_yields_no_triggers_or_clients():
    def fake(system, prompt, validate=None, retries=4):
        d = {"relevant_to_mfd_clients": False, "vanilla_summary": "No client action needed.",
             "circular_id": "ORDER-1", "triggers": []}
        return validate(d)
    s = _run(fake)
    assert s["impact_triggers"] == [] and s["affected_clients"] == []
    assert s["processing_errors"] == []
    card = s["action_cards"][0]
    # Nobody affected -> a labelled DEMO for 10 sample clients
    assert card["total_clients_affected"] == 0 and card["demo"] is True and len(card["clients"]) == 10


def test_trigger_needing_no_action_drops_clients():
    def fake(system, prompt, validate=None, retries=4):
        if "Process the following" in prompt:
            d = {"vanilla_summary": "s", "circular_id": "C", "triggers": [
                {"mandate_id": "T1", "rule_change": "r",
                 "client_filter": {"type": "category_holding", "categories": ["Small Cap"]}}]}
        else:
            d = {"T1": {"has_tax_implication": False, "tax_explanation": "n", "has_commission_impact": False,
                        "commission_explanation": "n", "client_action": "none", "urgency": "LOW",
                        "requires_client_action": False}}
        return validate(d) if validate else d
    s = _run(fake)
    assert s["affected_clients"] == [] and s["action_cards"][0]["total_clients_affected"] == 0
    assert s["action_cards"][0]["demo"] is True


def test_many_affected_clients_only_top_10_drafted_but_total_kept():
    def fake(system, prompt, validate=None, retries=4):
        import re
        if "Process the following" in prompt:
            d = {"vanilla_summary": "s", "circular_id": "C", "triggers": [
                {"mandate_id": "T1", "rule_change": "r",
                 "client_filter": {"type": "category_holding", "categories": ["Small Cap"]}}]}
        elif "Impact Triggers" in prompt:
            d = {"T1": {"has_tax_implication": False, "tax_explanation": "n", "has_commission_impact": False,
                        "commission_explanation": "n", "client_action": "act", "urgency": "HIGH",
                        "requires_client_action": True}}
        else:
            d = {i: "msg" for i in re.findall(r"ID:(CLT\d+)", prompt)}
        return validate(d) if validate else d
    from sentinel.graph import resume_review
    for m in (jc, be, dp):
        m.generate_json = fake
    app = build_graph()
    cfg = {"configurable": {"thread_id": "cap"}}
    s = app.invoke({"raw_circular_text": "x", "processing_errors": []}, cfg)
    card = s["action_cards"][0]
    assert card["demo"] is False and len(card["clients"]) == 10 and card["total_clients_affected"] > 10
    assert len(s["affected_clients"]) == card["total_clients_affected"]
    # redraft keeps the true total
    s = resume_review(app, cfg, approved=False, feedback="shorter")
    assert s["action_cards"][0]["total_clients_affected"] == card["total_clients_affected"]


def test_demo_fallback_message_never_claims_impact():
    """If the drafting call fails for an irrelevant circular, the template must not say 'affects your portfolio'."""
    def fake(system, prompt, validate=None, retries=4):
        if "Process the following" in prompt:
            return validate({"relevant_to_mfd_clients": False, "vanilla_summary": "No client action needed.",
                             "circular_id": "ORDER-1", "triggers": []})
        raise RuntimeError("429 quota")
    s = _run(fake)
    card = s["action_cards"][0]
    assert card["demo"] is True and card["clients"]
    for c in card["clients"]:
        msg = c["personalized_message"]
        assert "affects your portfolio" not in msg and "no action is needed" in msg
