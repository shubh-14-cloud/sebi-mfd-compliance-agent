import html
import time

import pandas as pd
import streamlit as st

from main import SAMPLE_CIRCULAR, fetch_live_circular
from sentinel.graph import build_graph, resume_review

st.set_page_config(page_title="Regulatory Sentinel", layout="wide", initial_sidebar_state="collapsed")

# ── Styling ──────────────────────────────────────────────────────────────────
st.markdown(
    """
<style>
  #MainMenu, footer, header [data-testid="stToolbar"] { visibility: hidden; }
  .block-container { padding-top: 2.2rem; padding-bottom: 4rem; max-width: 1180px; }
  h1, h2, h3 { letter-spacing: -0.01em; font-weight: 600; }
  h2 { font-size: 1.15rem; margin: 0 0 .25rem 0; padding-top: .25rem; }
  .app-title { font-size: 1.55rem; font-weight: 650; color: #14213d; margin: 0; }
  .app-sub { color: #5a6578; font-size: .92rem; margin: .15rem 0 1.2rem 0; }
  .rule { border: 0; border-top: 1px solid #dfe3ea; margin: 1.4rem 0 1.1rem 0; }
  .steps { display: flex; gap: 0; margin: 0 0 1.4rem 0; border: 1px solid #dfe3ea; border-radius: 4px; overflow: hidden; }
  .step { flex: 1; padding: .55rem .9rem; font-size: .82rem; color: #7a8497; background: #fff; border-right: 1px solid #dfe3ea; }
  .step:last-child { border-right: 0; }
  .step b { display: block; font-size: .68rem; letter-spacing: .06em; text-transform: uppercase; font-weight: 600; }
  .step.done { color: #1b3a63; background: #f4f6f9; }
  .step.now { color: #fff; background: #1b3a63; }
  .label { font-size: .7rem; letter-spacing: .06em; text-transform: uppercase; color: #6b7587; font-weight: 600; margin-bottom: .2rem; }
  .panel { border: 1px solid #dfe3ea; border-radius: 4px; padding: .9rem 1.1rem; background: #fff; }
  .panel p { margin: 0; line-height: 1.55; }
  .kpi { border: 1px solid #dfe3ea; border-radius: 4px; padding: .7rem 1rem; background: #fff; }
  .kpi .v { font-size: 1.45rem; font-weight: 650; color: #14213d; line-height: 1.2; }
  .kpi .v.sm { font-size: 1.02rem; padding-top: .3rem; overflow-wrap: anywhere; }
  .kpi .k { font-size: .7rem; letter-spacing: .06em; text-transform: uppercase; color: #6b7587; font-weight: 600; }
  .tag { display: inline-block; font-size: .68rem; font-weight: 600; letter-spacing: .05em; padding: .08rem .45rem;
         border-radius: 2px; border: 1px solid #c7cedb; color: #384357; background: #f4f6f9; vertical-align: middle; }
  .tag.high { border-color: #b7791f; color: #8a5a13; background: #fdf6e7; }
  .tag.critical { border-color: #b42318; color: #912018; background: #fdecea; }
  .tag.demo { border-color: #1b3a63; color: #1b3a63; background: #eef2f8; }
  .meta { color: #5a6578; font-size: .85rem; }
  .stButton > button { border-radius: 3px; font-weight: 600; font-size: .88rem; padding: .45rem 1.1rem; }
  div[data-testid="stExpander"] { border: 1px solid #dfe3ea; border-radius: 4px; background: #fff; }
  div[data-testid="stExpander"] summary { font-weight: 600; }
  textarea { font-size: .9rem !important; }
</style>
""",
    unsafe_allow_html=True,
)

# ── Session state ────────────────────────────────────────────────────────────
for key, default in {
    "circular_text": "",
    "graph_app": None,
    "snapshot": None,
    "approval_done": False,
    "final_state": None,
    "run_id": f"st-run-{int(time.time())}",
}.items():
    if key not in st.session_state:
        st.session_state[key] = default
if st.session_state.graph_app is None:
    st.session_state.graph_app = build_graph()


def _stage() -> int:
    """0 = circular, 2 = review, 3 = decided."""
    if st.session_state.approval_done:
        return 3
    return 2 if st.session_state.snapshot else 0


def _steps(active: int) -> str:
    names = ["Circular", "Analysis", "Review", "Decision"]
    parts = []
    for i, n in enumerate(names):
        cls = "now" if i == active else ("done" if i < active else "")
        parts.append(f'<div class="step {cls}"><b>Step {i + 1}</b>{n}</div>')
    return f'<div class="steps">{"".join(parts)}</div>'


def _tag(text: str) -> str:
    cls = text.lower() if text.lower() in {"high", "critical", "demo"} else ""
    return f'<span class="tag {cls}">{text}</span>'


def _kpi(label: str, value: str, small: bool = False) -> str:
    cls = "v sm" if small else "v"
    return f'<div class="kpi"><div class="k">{label}</div><div class="{cls}">{html.escape(value)}</div></div>'


# ── Header ───────────────────────────────────────────────────────────────────
st.markdown('<p class="app-title">Regulatory Sentinel</p>', unsafe_allow_html=True)
st.markdown(
    '<p class="app-sub">Mutual fund distributor compliance: from regulatory circular to reviewed client communication.</p>',
    unsafe_allow_html=True,
)
st.markdown(_steps(_stage()), unsafe_allow_html=True)

# ── 1. Circular ──────────────────────────────────────────────────────────────
st.markdown("## Circular")
st.markdown('<p class="meta">Fetch the latest SEBI circular, load the built-in sample, or paste text directly.</p>', unsafe_allow_html=True)

b1, b2, _ = st.columns([1.6, 1.6, 3.8])
with b1:
    if st.button("Fetch latest from SEBI", use_container_width=True):
        with st.spinner("Retrieving circular"):
            st.session_state.circular_text = fetch_live_circular()
        st.rerun()
with b2:
    if st.button("Load sample circular", use_container_width=True):
        st.session_state.circular_text = SAMPLE_CIRCULAR
        st.rerun()

st.session_state.circular_text = st.text_area(
    "Circular text",
    value=st.session_state.circular_text,
    height=190,
    label_visibility="collapsed",
    placeholder="Circular text appears here. It can be edited before analysis.",
)

st.markdown('<hr class="rule">', unsafe_allow_html=True)

# ── 2. Analysis ──────────────────────────────────────────────────────────────
st.markdown("## Analysis")
st.markdown(
    '<p class="meta">Extracts regulatory triggers, matches them against the client book, assesses tax and '
    'commission effects, and drafts messages for the most affected clients.</p>',
    unsafe_allow_html=True,
)
if st.button("Run analysis", type="primary", disabled=not st.session_state.circular_text.strip()):
    with st.spinner("Running analysis. This can take a minute on rate-limited API plans."):
        config = {"configurable": {"thread_id": st.session_state.run_id}}
        initial_state = {
            "raw_circular_text": st.session_state.circular_text,
            "circular_id": "",
            "vanilla_summary": "",
            "impact_triggers": [],
            "affected_clients": [],
            "mfd_commission_delta": {},
            "action_cards": [],
            "human_approval_status": False,
            "reviewer_feedback": "",
            "processing_errors": [],
        }
        st.session_state.snapshot = st.session_state.graph_app.invoke(initial_state, config)
        st.session_state.approval_done = False
        st.session_state.final_state = None
    st.rerun()

# ── 3. Review ────────────────────────────────────────────────────────────────
snapshot = st.session_state.snapshot
if snapshot:
    st.markdown('<hr class="rule">', unsafe_allow_html=True)
    st.markdown("## Review")

    errors = snapshot.get("processing_errors", [])
    if errors:
        with st.expander(f"Processing notes ({len(errors)})", expanded=True):
            for e in errors:
                st.markdown(f"- {e}")

    cards = snapshot.get("action_cards", [])
    if not cards:
        st.warning("No output was produced. Check the processing notes above.")

    for card in cards:
        demo = card.get("demo", False)
        comm = card.get("commission_impact", {}) or {}
        total = card.get("total_clients_affected", 0)
        shown = card.get("clients_shown", len(card.get("clients", [])))

        k1, k2, k3, k4 = st.columns(4)
        k1.markdown(_kpi("Circular", card.get("circular_reference", "Unknown"), small=True), unsafe_allow_html=True)
        k2.markdown(_kpi("Clients affected", f"{total:,}"), unsafe_allow_html=True)
        k3.markdown(_kpi("Drafts for review", f"{shown}"), unsafe_allow_html=True)
        k4.markdown(_kpi("Commission effect", "Yes" if comm.get("has_impact") else "None stated"), unsafe_allow_html=True)

        st.write("")
        st.markdown('<div class="label">Summary</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="panel"><p>{html.escape(card.get("vanilla_summary", ""))}</p></div>', unsafe_allow_html=True)

        if comm.get("has_impact"):
            st.write("")
            st.markdown('<div class="label">Commission note (internal, not for clients)</div>', unsafe_allow_html=True)
            st.markdown(
                f'<div class="panel"><p>{html.escape(comm.get("explanation", ""))}</p>'
                f'<p class="meta" style="margin-top:.4rem">{html.escape(comm.get("note", ""))}</p></div>',
                unsafe_allow_html=True,
            )

        triggers = snapshot.get("impact_triggers", [])
        if triggers:
            st.write("")
            st.markdown('<div class="label">Regulatory triggers</div>', unsafe_allow_html=True)
            st.dataframe(
                pd.DataFrame(
                    [
                        {
                            "ID": t.get("mandate_id"),
                            "Rule change": t.get("rule_change"),
                            "Severity": t.get("severity"),
                            "Applies to": t.get("client_filter", {}).get("type", "").replace("_", " "),
                            "Deadline": t.get("deadline") or "",
                        }
                        for t in triggers
                    ]
                ),
                hide_index=True,
                use_container_width=True,
            )

        st.write("")
        if demo:
            st.markdown(
                _tag("DEMO") + '&nbsp; <span class="meta">This circular affects no clients. The notes below are '
                "samples that show the output format only.</span>",
                unsafe_allow_html=True,
            )
        elif shown < total:
            st.markdown(
                f'<span class="meta">Drafts are shown for the {shown} most affected clients out of {total:,}.</span>',
                unsafe_allow_html=True,
            )
        st.markdown('<div class="label" style="margin-top:.6rem">Client communications</div>', unsafe_allow_html=True)

        for client in card.get("clients", []):
            urgency = client.get("urgency", "")
            head = f'{client.get("client_name")}  ({client.get("client_id")})'
            with st.expander(head, expanded=False):
                left, right = st.columns([1, 1.25], gap="large")
                with left:
                    if urgency:
                        st.markdown(_tag(urgency), unsafe_allow_html=True)
                    exposure = client.get("portfolio_exposure_pct")
                    if exposure:
                        st.markdown(f'<span class="meta">Portfolio exposure: {exposure}%</span>', unsafe_allow_html=True)
                    st.markdown('<div class="label" style="margin-top:.7rem">Reason</div>', unsafe_allow_html=True)
                    st.write(" ".join(client.get("reasons_for_impact", [])))
                    st.markdown('<div class="label" style="margin-top:.7rem">Tax</div>', unsafe_allow_html=True)
                    st.write(client.get("estimated_tax_impact", {}).get("explanation", "None"))
                    st.markdown('<div class="label" style="margin-top:.7rem">Recommended action</div>', unsafe_allow_html=True)
                    st.write(client.get("next_best_action", ""))
                with right:
                    st.markdown('<div class="label">Draft message (editable)</div>', unsafe_allow_html=True)
                    st.text_area(
                        "Draft message",
                        value=client.get("personalized_message", ""),
                        height=260,
                        key=f"msg_{client.get('client_id')}",
                        label_visibility="collapsed",
                    )

    # ── 4. Decision ──────────────────────────────────────────────────────────
    if cards:
        st.markdown('<hr class="rule">', unsafe_allow_html=True)
        st.markdown("## Decision")

        if not st.session_state.approval_done:
            if cards[0].get("demo"):
                st.markdown('<p class="meta">There is nothing to send for this circular.</p>', unsafe_allow_html=True)
            feedback = st.text_input(
                "Feedback for redraft",
                key="reviewer_feedback_input",
                placeholder="Optional. Used only if you request a revision.",
            )
            a, r, _ = st.columns([1, 1, 4])
            config = {"configurable": {"thread_id": st.session_state.run_id}}
            with a:
                if st.button("Approve", type="primary", use_container_width=True):
                    # Carry the reviewer's edits to the drafts into the graph state
                    edits = {
                        c["client_id"]: st.session_state.get(f"msg_{c['client_id']}", c.get("personalized_message", ""))
                        for card in cards
                        for c in card.get("clients", [])
                    }
                    with st.spinner("Finalising"):
                        st.session_state.final_state = resume_review(
                            st.session_state.graph_app, config, approved=True, edited_messages=edits
                        )
                        st.session_state.approval_done = True
                    st.rerun()
            with r:
                if st.button("Request revision", use_container_width=True):
                    with st.spinner("Redrafting with your feedback"):
                        # The graph returns to the Dispatcher and pauses at review again
                        st.session_state.snapshot = resume_review(
                            st.session_state.graph_app, config, approved=False, feedback=feedback
                        )
                        for k in [k for k in st.session_state if k.startswith("msg_")]:
                            del st.session_state[k]  # show the fresh drafts
                    st.rerun()
        elif st.session_state.final_state:
            final_cards = st.session_state.final_state.get("action_cards", [])
            n = len(final_cards[0].get("clients", [])) if final_cards else 0
            if final_cards and final_cards[0].get("demo"):
                st.success("Review complete. No client communications were required.")
            else:
                st.success(f"Approved. {n} client communication(s) are ready to dispatch.")
