# Agentic Regulatory Sentinel

> **Tier-1 MFD Compliance Automation** — a 4-node LangGraph agentic pipeline that ingests raw SEBI/AMFI circulars, cross-checks 650+ client portfolios, calculates tax & commission impacts, drafts personalised client messages, and gates dispatch behind a human-in-the-loop MFD review.

---

## What It Does

When SEBI or AMFI releases a regulatory circular, a Mutual Fund Distributor (MFD) must:

1. Understand the dense legal text.
2. Figure out which clients are affected (and how).
3. Calculate tax / commission implications.
4. Draft personalised communications for each affected client.
5. Review and approve before sending.

This pipeline automates steps 1–4 and puts the MFD firmly in control of step 5.

---

## Architecture

```
SEBI/AMFI Circular Text
        │
        ▼
┌───────────────────┐
│  Module 1         │  NLP parse → plain-English summary
│  Jargon-Cutter    │  + structured Impact Triggers JSON
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│  Module 2         │  Cross-checks 650+ mock client portfolios
│  Book Auditor     │  Identifies every affected client + why
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│  Module 3         │  1 LLM call → tax & commission analysis
│  Benefit Engine   │  Pure Python → applied per client (no extra LLM calls)
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│  Module 4         │  Batched LLM calls → personalised client emails
│  Dispatcher       │  Assembles Action Cards for MFD dashboard
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│  Human Review     │  ← LangGraph interrupt_before checkpoint
│  (MFD approves)   │  Approve → END   |   Reject → back to Dispatcher
└───────────────────┘
```

Full Mermaid diagram with state schema: [`architecture.md`](architecture.md)

---

## Project Structure

```
Circular/
├── main.py                        # Entry point — run the full pipeline
├── requirements.txt
├── .env.example                   # Copy to .env and add your Groq key
├── architecture.md                # Mermaid graph + data-flow diagram
│
├── sentinel/
│   ├── graph.py                   # LangGraph StateGraph builder
│   ├── state.py                   # GraphState TypedDict (shared state schema)
│   └── nodes/
│       ├── jargon_cutter.py       # Module 1 — NLP ingestion & translation
│       ├── book_auditor.py        # Module 2 — portfolio cross-check (deterministic)
│       ├── benefit_engine.py      # Module 3 — tax & commission engine
│       └── dispatcher.py          # Module 4 — action card & message generation
│
└── mock_data/
    └── portfolio_db.py            # 650-client mock MFD database (seeded, reproducible)
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Agent framework | [LangGraph](https://github.com/langchain-ai/langgraph) `>=0.2.0` |
| LLM | `llama-3.3-70b-versatile` via [Groq](https://groq.com) |
| State persistence | LangGraph `MemorySaver` (in-memory checkpointer) |
| Human-in-the-loop | LangGraph `interrupt_before=["human_review"]` |
| Data validation | Pydantic `>=2.0` |
| Config | `python-dotenv` |
| Language | Python 3.11+ |

---

## Quickstart

### 1. Clone & install dependencies

```bash
git clone https://github.com/<your-username>/agentic-regulatory-sentinel.git
cd agentic-regulatory-sentinel

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### 2. Set your Groq API key

```bash
cp .env.example .env
# Edit .env and paste your key:
# GROQ_API_KEY=gsk_...
```

Get a free key at [console.groq.com](https://console.groq.com).

### 3. Run the pipeline

```bash
python main.py
```

**Phase 1** runs automatically through all 4 modules and pauses at the Human Review checkpoint, printing Action Cards to the terminal.

**Phase 2** prompts you (`y/n`) to simulate MFD approval, then resumes the graph.

Full output is saved to `sentinel_output.json`.

---

## LangGraph Graph Topology

```
START
  → ingest_circular   (Jargon-Cutter)
  → audit_book        (Book Auditor)
  → calculate_benefits(Benefit Engine)
  → stage_dispatch    (Dispatcher)
  → human_review      ── interrupt_before ──┐
      ├─ approved  → END                    │
      └─ rejected  → stage_dispatch ────────┘
```

The graph is compiled with a `MemorySaver` checkpointer so state is preserved across the interrupt boundary. Resume by invoking the graph on the **same `thread_id`** with `{"human_approval_status": True/False}`.

---

## Module Details

### Module 1 — Jargon-Cutter (`jargon_cutter.py`)
- Sends raw circular text to the LLM with a structured system prompt.
- Extracts a **Vanilla Summary** (plain English, safe for clients) and a typed **Impact Triggers JSON** listing every distinct regulatory change with `fund_categories_impacted`, `client_filter` criteria, `severity`, and deadline dates.

### Module 2 — Book Auditor (`book_auditor.py`)
- **No LLM calls** — fully deterministic.
- Queries the mock 650-client portfolio database using trigger `client_filter` criteria (`category_holding`, `no_nomination`, `kyc_pending`, `all`).
- Deduplicates clients hit by multiple triggers, computes per-client `portfolio_exposure_pct`, and generates a personalised reason-for-impact string.

### Module 3 — Benefit Engine (`benefit_engine.py`)
- **1 LLM call** to analyse all triggers: does this circular cause tax events? what does it say about commissions?
- **Pure Python loop** applies that analysis to every affected client — no per-client LLM calls regardless of client count.
- Fiduciary constraint: tax and commission implications are derived exclusively from what the circular actually states — no hardcoded assumptions.

### Module 4 — Dispatcher (`dispatcher.py`)
- Batches clients (15 per call) and drafts personalised 3-paragraph client emails via LLM.
- Assembles **Action Cards** — the structured payload the MFD reviews before dispatch.
- Falls back to template messages if a batch LLM call fails.

---

## Mock Database

`mock_data/portfolio_db.py` generates a reproducible 650-client MFD book of business (`random.seed(42)`) covering 12 fund categories:

`Small Cap · Mid Cap · Large Cap · ELSS · Liquid · Short Duration Debt · Corporate Bond · Flexi Cap · Multi Cap · Index Fund · International Fund · Gold Fund`

Each client has randomised name, PAN, email, phone, risk profile, tax bracket, KYC status, nomination status, SIP flag, and 1–6 fund holdings with realistic ISIN codes, NAVs, invested amounts, and holding periods.

---

## Fiduciary Design Principles

- **No invented tax implications** — a TER reduction or nomination mandate does not trigger capital gains events. The engine only flags tax implications when the circular explicitly causes redemptions or reclassifications.
- **No commission-driven advice** — client messages never mention distributor earnings or suggest fund switches to offset regulatory changes.
- **MFD always in the loop** — no messages are dispatched without explicit human approval.

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `GROQ_API_KEY` | ✅ | Groq API key for LLM inference |

---

## License

MIT
