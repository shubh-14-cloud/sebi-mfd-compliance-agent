# Agentic Regulatory Sentinel — Architecture

## LangGraph State Machine

```mermaid
flowchart TD
    START([START]) --> JC

    subgraph M1["Module 1 · Jargon-Cutter"]
        JC["ingest_circular\nNLP Ingestion & Translation"]
    end

    subgraph M2["Module 2 · Autonomous Book Auditor"]
        BA["audit_book\nPortfolio Cross-Check\n650+ client portfolios"]
    end

    subgraph M3["Module 3 · Benefit & Reality Engine"]
        BE["calculate_benefits\nLTCG/STCG Tax Calc\nCommission Delta"]
    end

    subgraph M4["Module 4 · Ready-to-Act Dispatcher"]
        DS["stage_dispatch\nAction Card Generation\nPersonalized Messages"]
    end

    subgraph HITL["Human-in-the-Loop"]
        HR{"human_review\nMFD Reviews\nAction Cards"}
    end

    JC --> BA
    BA --> BE
    BE --> DS
    DS --> HR
    HR -->|"approved = True"| END_NODE([END])
    HR -->|"approved = False\nrevision needed"| DS

    subgraph STATE["GraphState — persisted across all nodes"]
        direction LR
        s1["raw_circular_text: str"]
        s2["vanilla_summary: str"]
        s3["impact_triggers: List[dict]"]
        s4["affected_clients: List[dict]"]
        s5["mfd_commission_delta: float"]
        s6["action_cards: List[dict]"]
        s7["human_approval_status: bool"]
        s8["circular_id: str"]
        s9["processing_errors: List[str]"]
    end
```

## Node Responsibilities

| Node | Module | Input | Output |
|------|--------|-------|--------|
| `ingest_circular` | Jargon-Cutter | `raw_circular_text` | `vanilla_summary`, `impact_triggers`, `circular_id` |
| `audit_book` | Book Auditor | `impact_triggers` | `affected_clients` |
| `calculate_benefits` | Benefit Engine | `affected_clients`, `impact_triggers` | `mfd_commission_delta`, enriched `affected_clients` |
| `stage_dispatch` | Dispatcher | All state | `action_cards` |
| `human_review` | HITL | `action_cards` | `human_approval_status` |

## Data Flow

```
SEBI/AMFI Circular PDF Text
        │
        ▼
[Jargon-Cutter] ──► Vanilla Summary (plain English)
        │            Impact Triggers JSON
        │              ├─ mandate_id
        │              ├─ rule_change
        │              ├─ fund_categories_impacted
        │              ├─ effective_date / deadline
        │              └─ client_filter criteria
        │
        ▼
[Book Auditor] ──► Affected Clients List
        │            Per client:
        │              ├─ client_id, name
        │              ├─ affected_holdings
        │              └─ reason_for_impact (personalized)
        │
        ▼
[Benefit Engine] ──► Per client: LTCG/STCG tax impact
        │                         next_best_action
        │            MFD-level: commission_delta estimate
        │
        ▼
[Dispatcher] ──► Action Cards (dashboard payload)
        │          Per card:
        │            ├─ vanilla_summary
        │            ├─ impacted client list
        │            ├─ commission_delta
        │            └─ pre-drafted personalized messages
        │
        ▼
[Human Review] ──► MFD approves → END
   (interrupt)      MFD rejects → back to Dispatcher
```
