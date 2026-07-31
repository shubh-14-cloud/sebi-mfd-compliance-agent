import streamlit as st
import time
from sentinel.graph import build_graph
from main import fetch_live_circular

st.set_page_config(page_title="Regulatory Sentinel", layout="wide")

st.title("🛡️ Agentic Regulatory Sentinel")
st.markdown("Tier-1 MFD Compliance Automation — Powered by LangGraph + Claude")

# Initialize session state variables
if "circular_text" not in st.session_state:
    st.session_state.circular_text = ""
if "graph_app" not in st.session_state:
    st.session_state.graph_app = build_graph()
if "snapshot" not in st.session_state:
    st.session_state.snapshot = None
if "approval_done" not in st.session_state:
    st.session_state.approval_done = False
if "final_state" not in st.session_state:
    st.session_state.final_state = None
if "run_id" not in st.session_state:
    st.session_state.run_id = f"st-run-{int(time.time())}"

# 1. Fetch Section
st.header("1. Circular Ingestion")
col1, col2 = st.columns([1, 1])

with col1:
    if st.button("Fetch Live Circular from SEBI"):
        with st.spinner("Fetching RSS feed and extracting PDF document..."):
            st.session_state.circular_text = fetch_live_circular()
        st.success("Successfully fetched latest circular!")

with col2:
    st.session_state.circular_text = st.text_area(
        "Raw Circular Text", 
        value=st.session_state.circular_text, 
        height=200,
        help="You can manually edit the circular text here before processing."
    )

# 2. Process Section
st.header("2. AI Analysis Pipeline")
if st.button("Run Compliance Pipeline", disabled=not st.session_state.circular_text):
    with st.spinner("Processing through Module 1 → Jargon-Cutter..."):
        time.sleep(1)
    with st.spinner("Processing through Module 2 → Book Auditor..."):
        time.sleep(1)
    with st.spinner("Processing through Module 3 → Benefit Engine..."):
        time.sleep(1)
    with st.spinner("Processing through Module 4 → Dispatcher..."):
        config = {"configurable": {"thread_id": st.session_state.run_id}}
        
        initial_state = {
            "raw_circular_text": st.session_state.circular_text,
            "circular_id": "",
            "vanilla_summary": "",
            "impact_triggers": [],
            "affected_clients": [],
            "mfd_commission_delta": 0.0,
            "action_cards": [],
            "human_approval_status": False,
            "processing_errors": [],
        }
        
        st.session_state.snapshot = st.session_state.graph_app.invoke(initial_state, config)
        st.session_state.approval_done = False
        st.session_state.final_state = None
    
    st.success("Pipeline paused at Human Review checkpoint!")

# 3. Review Section
if st.session_state.snapshot:
    st.header("3. Human-in-the-Loop Review")
    
    action_cards = st.session_state.snapshot.get("action_cards", [])
    errors = st.session_state.snapshot.get("processing_errors", [])
    
    if errors:
        st.error(f"Processing Errors: {errors}")
        
    if not action_cards:
        st.warning("No Action Cards generated.")
    else:
        for card in action_cards:
            with st.expander(f"Action Card: {card.get('circular_reference', 'Unknown')}", expanded=True):
                st.write(f"**Vanilla Summary:** {card.get('vanilla_summary')}")
                comm = card.get('commission_impact', {})
                if comm.get('has_impact'):
                    st.warning(f"**Commission Impact:** {comm.get('explanation')}\n\n*Note: {comm.get('note', '')}*")
                else:
                    st.info(f"**Commission Impact:** {comm.get('explanation', 'None')}")
                
                st.write(f"**Total Clients Affected:** {card.get('total_clients_affected')}")
                
                st.subheader("Client Actions")
                clients = card.get("clients", [])
                for client in clients:
                    st.markdown(f"**{client.get('client_name')}** ({client.get('client_id')})")
                    st.write(f"- **Impact:** {'; '.join(client.get('reasons_for_impact', []))}")
                    st.write(f"- **Tax:** {client.get('estimated_tax_impact', {}).get('explanation', 'None')}")
                    st.write(f"- **Next Best Action:** {client.get('next_best_action')}")
                    st.text_area("Draft Message", value=client.get('personalized_message'), height=100, key=f"msg_{client.get('client_id')}")
                    st.divider()

    if not st.session_state.approval_done:
        col_app, col_rej = st.columns([1, 1])
        with col_app:
            if st.button("✅ Approve & Dispatch", type="primary"):
                config = {"configurable": {"thread_id": st.session_state.run_id}}
                with st.spinner("Resuming graph with approval..."):
                    st.session_state.final_state = st.session_state.graph_app.invoke({"human_approval_status": True}, config)
                    st.session_state.approval_done = True
                st.rerun()
                
        with col_rej:
            if st.button("❌ Reject & Revise"):
                config = {"configurable": {"thread_id": st.session_state.run_id}}
                with st.spinner("Resuming graph with rejection..."):
                    st.session_state.final_state = st.session_state.graph_app.invoke({"human_approval_status": False}, config)
                    st.session_state.approval_done = True
                st.rerun()

    if st.session_state.approval_done and st.session_state.final_state:
        approved = st.session_state.final_state.get("human_approval_status")
        if approved:
            cards = st.session_state.final_state.get("action_cards", [])
            total = len(cards[0].get("clients", [])) if cards else 0
            st.success(f"🎉 Pipeline complete! {total} personalised client message(s) approved and ready to dispatch.")
        else:
            st.warning("↺ Action Cards sent back to Dispatcher for revision.")
