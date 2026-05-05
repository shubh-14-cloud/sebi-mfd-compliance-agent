const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Header, Footer, AlignmentType, LevelFormat, BorderStyle, WidthType,
  ShadingType, HeadingLevel, PageNumber, PageBreak, VerticalAlign,
  TabStopType, TabStopPosition
} = require("docx");
const fs = require("fs");

// ── Palette ────────────────────────────────────────────────────────────────
const NAVY      = "1B3A6B";
const BLUE      = "2E75B6";
const LIGHTBLUE = "D6E8F7";
const PALE      = "EEF4FB";
const WHITE     = "FFFFFF";
const DARKGRAY  = "333333";
const MIDGRAY   = "555555";
const LINECOLOR = "BFCFE8";

// ── Widths (A4, 1 inch margins → content = 9026 DXA) ──────────────────────
const CONTENT_W = 9026;

// ── Helpers ────────────────────────────────────────────────────────────────
const border = (color = LINECOLOR) => ({ style: BorderStyle.SINGLE, size: 1, color });
const allBorders = (color = LINECOLOR) => ({ top: border(color), bottom: border(color), left: border(color), right: border(color) });
const noBorders = () => ({
  top: { style: BorderStyle.NONE, size: 0, color: WHITE },
  bottom: { style: BorderStyle.NONE, size: 0, color: WHITE },
  left: { style: BorderStyle.NONE, size: 0, color: WHITE },
  right: { style: BorderStyle.NONE, size: 0, color: WHITE },
});

const spacer = (before = 0, after = 120) => new Paragraph({
  children: [new TextRun("")],
  spacing: { before, after },
});

const divider = () => new Paragraph({
  children: [new TextRun("")],
  border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: BLUE, space: 1 } },
  spacing: { before: 80, after: 160 },
});

// ── Text helpers ───────────────────────────────────────────────────────────
const h1 = (text) => new Paragraph({
  heading: HeadingLevel.HEADING_1,
  children: [new TextRun({ text, font: "Arial", size: 36, bold: true, color: NAVY })],
  spacing: { before: 400, after: 160 },
});

const h2 = (text) => new Paragraph({
  heading: HeadingLevel.HEADING_2,
  children: [new TextRun({ text, font: "Arial", size: 26, bold: true, color: BLUE })],
  spacing: { before: 280, after: 120 },
});

const h3 = (text) => new Paragraph({
  heading: HeadingLevel.HEADING_3,
  children: [new TextRun({ text, font: "Arial", size: 22, bold: true, color: NAVY })],
  spacing: { before: 200, after: 80 },
});

const body = (text, opts = {}) => new Paragraph({
  children: [new TextRun({ text, font: "Arial", size: 22, color: DARKGRAY, ...opts })],
  spacing: { before: 60, after: 100 },
  alignment: AlignmentType.JUSTIFIED,
});

const bodyBold = (label, rest) => new Paragraph({
  children: [
    new TextRun({ text: label, font: "Arial", size: 22, bold: true, color: NAVY }),
    new TextRun({ text: rest, font: "Arial", size: 22, color: DARKGRAY }),
  ],
  spacing: { before: 60, after: 100 },
});

const bullet = (text, bold = "") => new Paragraph({
  numbering: { reference: "bullets", level: 0 },
  children: bold
    ? [new TextRun({ text: bold, font: "Arial", size: 22, bold: true, color: NAVY }),
       new TextRun({ text, font: "Arial", size: 22, color: DARKGRAY })]
    : [new TextRun({ text, font: "Arial", size: 22, color: DARKGRAY })],
  spacing: { before: 40, after: 60 },
});

const code = (text) => new Paragraph({
  children: [new TextRun({ text, font: "Courier New", size: 18, color: "1A1A2E" })],
  shading: { fill: "F0F4FF", type: ShadingType.CLEAR },
  spacing: { before: 40, after: 40 },
  indent: { left: 360 },
});

// ── Table helpers ──────────────────────────────────────────────────────────
const headerCell = (text, w) => new TableCell({
  width: { size: w, type: WidthType.DXA },
  borders: allBorders(BLUE),
  shading: { fill: NAVY, type: ShadingType.CLEAR },
  margins: { top: 100, bottom: 100, left: 140, right: 140 },
  children: [new Paragraph({
    children: [new TextRun({ text, font: "Arial", size: 20, bold: true, color: WHITE })],
    alignment: AlignmentType.LEFT,
  })],
});

const dataCell = (text, w, shade = WHITE, bold = false) => new TableCell({
  width: { size: w, type: WidthType.DXA },
  borders: allBorders(LINECOLOR),
  shading: { fill: shade, type: ShadingType.CLEAR },
  margins: { top: 80, bottom: 80, left: 140, right: 140 },
  verticalAlign: VerticalAlign.CENTER,
  children: [new Paragraph({
    children: [new TextRun({ text, font: "Arial", size: 20, color: bold ? NAVY : DARKGRAY, bold })],
  })],
});

const makeTable = (colWidths, headerTexts, rows) => {
  const totalW = colWidths.reduce((a, b) => a + b, 0);
  return new Table({
    width: { size: totalW, type: WidthType.DXA },
    columnWidths: colWidths,
    rows: [
      new TableRow({
        tableHeader: true,
        children: headerTexts.map((t, i) => headerCell(t, colWidths[i])),
      }),
      ...rows.map((row, ri) =>
        new TableRow({
          children: row.map((cell, ci) => {
            const shade = ri % 2 === 0 ? WHITE : PALE;
            if (typeof cell === "object" && cell.text !== undefined) {
              return dataCell(cell.text, colWidths[ci], shade, cell.bold);
            }
            return dataCell(cell, colWidths[ci], shade, ci === 0);
          }),
        })
      ),
    ],
  });
};

// ── Callout box ────────────────────────────────────────────────────────────
const callout = (text) => new Table({
  width: { size: CONTENT_W, type: WidthType.DXA },
  columnWidths: [200, CONTENT_W - 200],
  rows: [new TableRow({ children: [
    new TableCell({
      width: { size: 200, type: WidthType.DXA },
      borders: noBorders(),
      shading: { fill: BLUE, type: ShadingType.CLEAR },
      margins: { top: 100, bottom: 100, left: 120, right: 120 },
      children: [new Paragraph({ children: [new TextRun({ text: "KEY", font: "Arial", size: 18, bold: true, color: WHITE })], alignment: AlignmentType.CENTER })],
    }),
    new TableCell({
      width: { size: CONTENT_W - 200, type: WidthType.DXA },
      borders: { top: border(BLUE), bottom: border(BLUE), left: border(BLUE), right: border(BLUE) },
      shading: { fill: LIGHTBLUE, type: ShadingType.CLEAR },
      margins: { top: 100, bottom: 100, left: 160, right: 160 },
      children: [new Paragraph({ children: [new TextRun({ text, font: "Arial", size: 21, color: NAVY, italics: true })] })],
    }),
  ]})],
});

// ══════════════════════════════════════════════════════════════════════════
// DOCUMENT CONTENT
// ══════════════════════════════════════════════════════════════════════════

const children = [];

// ── COVER PAGE ─────────────────────────────────────────────────────────────
children.push(
  new Paragraph({ children: [new TextRun("")], spacing: { before: 2400, after: 0 } }),

  new Paragraph({
    children: [new TextRun({ text: "AGENTIC REGULATORY SENTINEL", font: "Arial", size: 56, bold: true, color: NAVY })],
    alignment: AlignmentType.CENTER,
    spacing: { before: 0, after: 80 },
  }),
  new Paragraph({
    children: [new TextRun({ text: "v1.0", font: "Arial", size: 36, bold: true, color: BLUE })],
    alignment: AlignmentType.CENTER,
    spacing: { before: 0, after: 200 },
  }),

  new Paragraph({
    children: [new TextRun("")],
    border: { bottom: { style: BorderStyle.SINGLE, size: 12, color: BLUE, space: 1 } },
    spacing: { before: 0, after: 200 },
  }),

  new Paragraph({
    children: [new TextRun({ text: "Technical Project Report  |  Interview Showcase", font: "Arial", size: 28, color: MIDGRAY, italics: true })],
    alignment: AlignmentType.CENTER,
    spacing: { before: 200, after: 120 },
  }),
  new Paragraph({
    children: [new TextRun({ text: "LangGraph  \u00B7  Python  \u00B7  Groq (Llama 3.3 70B)  \u00B7  Agentic AI", font: "Arial", size: 22, color: BLUE })],
    alignment: AlignmentType.CENTER,
    spacing: { before: 0, after: 600 },
  }),

  new Paragraph({ children: [new TextRun("")], spacing: { before: 600, after: 0 } }),

  // Metrics row
  makeTable(
    [2255, 2256, 2255, 2260],
    ["Portfolios Audited", "Clients Identified", "API Calls (Optimised)", "Modules"],
    [["650+", "403", "~28", "4 Nodes"]]
  ),

  new Paragraph({ children: [new TextRun("")], spacing: { before: 600, after: 0 } }),
  new Paragraph({
    children: [new TextRun({ text: "April 2026", font: "Arial", size: 22, color: MIDGRAY })],
    alignment: AlignmentType.CENTER,
  }),

  new Paragraph({ children: [new PageBreak()] }),
);

// ── 1. EXECUTIVE SUMMARY ────────────────────────────────────────────────────
children.push(
  h1("1. Executive Summary"),
  divider(),
  body(
    "The Agentic Regulatory Sentinel is a production-grade, stateful AI system built for Tier-1 " +
    "Mutual Fund Distributors (MFDs) operating in the Indian financial market. It fully automates " +
    "the compliance workflow triggered by SEBI and AMFI regulatory circulars — a process that " +
    "previously required hours of manual effort per circular."
  ),
  body(
    "The system ingests raw circular text, translates dense legal language into plain English, " +
    "autonomously audits an entire book of 650+ client portfolios to identify who is impacted, " +
    "determines whether the circular causes any tax or commission implications (based solely on " +
    "the circular's own content — never hardcoded assumptions), and stages pre-drafted, " +
    "personalised client communications for a final human-in-the-loop approval step."
  ),
  spacer(80, 80),
  callout(
    "Core Fiduciary Constraint: The system always prioritises client benefit. It never suggests " +
    "portfolio changes to recover distributor commission losses. Commission impact is surfaced " +
    "as transparent, informational context only."
  ),
  spacer(160),

  h2("Key Outcomes"),
  makeTable(
    [3200, 5826],
    ["Metric", "Result"],
    [
      ["Portfolios scanned per circular", "650 (full book, autonomous)"],
      ["Clients identified as affected", "403 (SEBI/HO/IMD/2024/053 demo run)"],
      ["Total LLM API calls (optimised)", "~28 (vs 800+ naive approach)"],
      ["Benefit Engine LLM calls", "1 (single trigger analysis call)"],
      ["Dispatcher LLM calls", "~27 (batched 15 clients / call)"],
      ["Tax calculation approach", "Circular-driven — zero hardcoded rates"],
      ["Human approval mechanism", "LangGraph interrupt + MemorySaver checkpoint"],
    ]
  ),
  spacer(200),
);

// ── 2. PROBLEM STATEMENT ─────────────────────────────────────────────────────
children.push(
  h1("2. Problem Statement"),
  divider(),
  body(
    "When SEBI or AMFI issues a regulatory circular, a Mutual Fund Distributor faces an " +
    "intensive, error-prone manual workflow:"
  ),
  spacer(60),

  bullet("Read and interpret a dense, legally worded circular document — often 5-15 pages"),
  bullet("Manually open the book of business and scroll through 650+ individual client portfolios"),
  bullet("Identify which clients hold the fund categories or meet the criteria specified in the circular"),
  bullet("Calculate whether the regulatory change triggers any tax events (LTCG, STCG) for each client"),
  bullet("Estimate how the change affects the MFD\u2019s own trail commission income"),
  bullet("Type individual, personalised emails to each affected client explaining the change"),
  bullet("Track responses and ensure compliance deadlines are met"),
  spacer(120),

  body(
    "This process typically takes 4-8 hours per circular, is highly susceptible to human error " +
    "(missed clients, incorrect tax interpretations, generic rather than personalised messaging), " +
    "and creates significant compliance risk if deadlines are missed. For a Tier-1 MFD managing " +
    "crores in AUM across hundreds of clients, this is not a sustainable workflow."
  ),
  spacer(160),
);

// ── 3. SOLUTION ARCHITECTURE ─────────────────────────────────────────────────
children.push(
  h1("3. Solution Architecture"),
  divider(),
  body(
    "The Sentinel is implemented as a LangGraph stateful state machine — a directed graph of " +
    "AI nodes that share a persistent state object (GraphState). LangGraph was chosen over " +
    "standard LLM chains because the system must maintain the full context of circular rules " +
    "while looping through hundreds of distinct portfolio states, and must support a hard " +
    "pause-and-resume for the human approval step."
  ),
  spacer(120),

  h2("Pipeline Flow"),
  spacer(60),

  makeTable(
    [400, 2000, 2800, 3826],
    ["Step", "Node", "Function", "Output"],
    [
      ["1", "ingest_circular", "Jargon-Cutter (Module 1)", "vanilla_summary + impact_triggers JSON"],
      ["2", "audit_book", "Book Auditor (Module 2)", "403 affected clients + impact reasons"],
      ["3", "calculate_benefits", "Benefit Engine (Module 3)", "Tax analysis + commission summary"],
      ["4", "stage_dispatch", "Dispatcher (Module 4)", "Action Cards + 403 personalised messages"],
      ["5", "human_review", "HITL Interrupt", "MFD approves or requests revision"],
      ["6", "END / loop", "Conditional Edge", "Approved \u2192 END | Rejected \u2192 Dispatcher"],
    ]
  ),
  spacer(120),

  h2("Graph Topology (LangGraph)"),
  spacer(40),
  code("START"),
  code("  \u2192 ingest_circular    (Module 1)"),
  code("  \u2192 audit_book         (Module 2)"),
  code("  \u2192 calculate_benefits (Module 3)"),
  code("  \u2192 stage_dispatch     (Module 4)"),
  code("  \u2192 human_review       \u2190\u2500 interrupt_before "),
  code("      \u251C\u2500 approved  \u2192 END"),
  code("      \u2514\u2500 rejected  \u2192 stage_dispatch  (revision loop)"),
  spacer(160),
);

// ── 4. TECHNOLOGY STACK ───────────────────────────────────────────────────────
children.push(
  h1("4. Technology Stack"),
  divider(),
  makeTable(
    [2200, 2200, 4626],
    ["Layer", "Technology", "Why This Choice"],
    [
      ["Orchestration", "LangGraph >= 0.2", "Stateful graph with interrupt/resume, MemorySaver checkpoints, and conditional edges — necessary for the HITL loop"],
      ["Language Model", "Groq / Llama-3.3-70B-Versatile", "Sub-second inference, high context window, strong instruction-following for JSON extraction"],
      ["Language", "Python 3.13", "Native LangGraph support, strong data science ecosystem"],
      ["State Schema", "TypedDict (typing_extensions)", "Zero-overhead, LangGraph-native, IDE type-safe"],
      ["Env Management", "python-dotenv", "Secure key loading independent of working directory"],
      ["Mock Database", "Pure Python (random.seed=42)", "Reproducible 650-client dataset, 12 fund categories, real ISINs"],
      ["Output Validation", "Built-in JSON + regex", "Strip markdown fences, fallback templates on parse failure"],
    ]
  ),
  spacer(200),
);

// ── 5. MODULE DEEP-DIVES ──────────────────────────────────────────────────────
children.push(
  h1("5. Module Deep-Dives"),
  divider(),
);

// 5.1
children.push(
  h2("5.1  Module 1 \u2014 The Jargon-Cutter"),
  h3("Node: ingest_circular  |  LLM Calls: 1"),
  body(
    "The Jargon-Cutter is the entry point of the pipeline. It sends the raw circular text to the " +
    "LLM in a single structured prompt and extracts two outputs simultaneously:"
  ),
  spacer(60),
  bodyBold("Vanilla Summary: ", "3-5 plain-English sentences that a non-expert MFD can read, " +
    "understand, and safely forward to a client. No legal terminology, no jargon."),
  bodyBold("Impact Triggers JSON: ", "A structured list of every distinct regulatory change " +
    "extracted from the circular. Each trigger contains a mandate ID, the rule change description, " +
    "fund categories impacted, effective date, deadline, and a client_filter specification."),
  spacer(80),

  h3("Impact Trigger Schema"),
  code('{ "mandate_id": "T001",'),
  code('  "rule_change": "TER cap reduced from 1.05% to 0.85% for Small Cap funds",'),
  code('  "fund_categories_impacted": ["Small Cap"],'),
  code('  "client_filter": { "type": "category_holding", "categories": ["Small Cap"] },'),
  code('  "severity": "MEDIUM",'),
  code('  "effective_date": "2024-06-01",'),
  code('  "deadline": null }'),
  spacer(80),

  body(
    "The client_filter.type field is the critical output — it instructs Module 2 exactly how to " +
    "query the portfolio database. Valid types are: category_holding, no_nomination, kyc_pending, all."
  ),
  spacer(160),
);

// 5.2
children.push(
  h2("5.2  Module 2 \u2014 The Autonomous Book Auditor"),
  h3("Node: audit_book  |  LLM Calls: 0"),
  body(
    "The Book Auditor replaces the manual portfolio search entirely. It takes the Impact Triggers " +
    "from Module 1 and runs deterministic database queries against the 650-client mock portfolio " +
    "database to identify exactly which clients are affected and why."
  ),
  spacer(60),

  makeTable(
    [2800, 3000, 3226],
    ["client_filter.type", "Database Query", "Example Use Case"],
    [
      ["category_holding", "get_clients_by_categories([...])", "Clients holding Small Cap / Mid Cap funds"],
      ["no_nomination", "get_clients_without_nomination()", "Accounts without a linked nominee"],
      ["kyc_pending", "get_clients_with_pending_kyc()", "Clients with incomplete KYC"],
      ["all", "get_all_clients()", "Universal compliance mandates"],
    ]
  ),
  spacer(80),

  body(
    "For each matched client, the auditor extracts only the specific affected holdings, calculates " +
    "the portfolio exposure percentage, and generates a personalised reason-for-impact string — " +
    "entirely through string formatting with no LLM call. Clients hit by multiple triggers are " +
    "deduplicated and merged into a single enriched record."
  ),
  spacer(160),
);

// 5.3
children.push(
  h2("5.3  Module 3 \u2014 The Benefit & Reality Engine"),
  h3("Node: calculate_benefits  |  LLM Calls: 1"),
  body(
    "This is the most architecturally significant module, and the one that underwent the most " +
    "important design revision during development. The initial implementation used hardcoded " +
    "tax rates (12.5% LTCG, 20% STCG) applied to every client regardless of what the circular " +
    "actually said. This was fundamentally wrong — a TER reduction circular causes no tax event " +
    "at all, yet the engine was calculating tax liabilities for every affected client."
  ),
  spacer(80),
  callout(
    "Redesign Principle: All tax and commission analysis must be derived exclusively from the " +
    "circular\u2019s own content. If the circular does not cause a tax event, no tax is surfaced. " +
    "If the circular does not state specific commission figures, no figures are assumed."
  ),
  spacer(120),

  h3("How It Works"),
  body(
    "A single LLM call analyzes all impact triggers against the circular summary and returns a " +
    "structured analysis per trigger-ID:"
  ),
  spacer(60),

  makeTable(
    [2600, 6426],
    ["Analysis Field", "Description"],
    [
      ["has_tax_implication", "True only if the circular forces a redemption, switch, or reclassification that changes tax treatment"],
      ["tax_explanation", "Specific explanation of the tax situation — what type, under what conditions, for this circular"],
      ["has_commission_impact", "True if the circular changes TER, trail commission, or GST treatment"],
      ["commission_explanation", "Uses ONLY actual percentages stated in the circular. Never estimates."],
      ["client_action", "Trigger-specific 1-2 sentence action for affected clients"],
      ["urgency", "LOW / MEDIUM / HIGH / CRITICAL based on the circular\u2019s deadline and severity"],
    ]
  ),
  spacer(80),

  body(
    "This analysis map is then applied to all 403 clients in pure Python — no additional LLM " +
    "calls regardless of client count. Each client inherits the analysis for their specific " +
    "triggered mandates. The commission summary uses only the actual TER figures the circular " +
    "states, with a clear disclaimer if no figures are specified."
  ),
  spacer(160),
);

// 5.4
children.push(
  h2("5.4  Module 4 \u2014 The Ready-to-Act Dispatcher"),
  h3("Node: stage_dispatch  |  LLM Calls: ~27 (batched)"),
  body(
    "The Dispatcher assembles the final Action Card payload for the MFD dashboard. Its primary " +
    "task is drafting a personalised email for every one of the 403 affected clients."
  ),
  spacer(60),

  h3("Batch Optimisation"),
  body(
    "A naive implementation would make one LLM API call per client — 403 calls. This caused the " +
    "pipeline to stall. The solution was to batch clients into groups of 15 per LLM call. Each " +
    "call receives 15 client briefs and returns a JSON object of {client_id: message}. This " +
    "reduced 403 sequential calls to ~27 batched calls with no loss in personalisation quality."
  ),
  spacer(80),

  makeTable(
    [3000, 3013, 3013],
    ["Approach", "API Calls", "Result"],
    [
      ["Naive (1 call / client)", "403", "Pipeline stalls — minutes per run"],
      ["Batched (15 clients / call)", "~27", "Completes in seconds"],
    ]
  ),
  spacer(80),

  body(
    "Each Action Card contains: the circular reference and vanilla summary, the total count of " +
    "affected clients, the commission impact summary (circular-derived), and the full list of " +
    "clients with their personalised draft messages, tax analysis, next best action, and urgency level."
  ),
  spacer(160),
);

// ── 6. GRAPHSTATE ──────────────────────────────────────────────────────────────
children.push(
  h1("6. GraphState \u2014 The Shared Memory"),
  divider(),
  body(
    "GraphState is a TypedDict that acts as the single source of truth across the entire " +
    "pipeline. LangGraph merges partial dict returns from each node into the running state, " +
    "so each module only writes the fields it owns without overwriting anything else."
  ),
  spacer(80),

  makeTable(
    [2800, 1400, 4826],
    ["Field", "Type", "Owner & Purpose"],
    [
      ["raw_circular_text", "str", "Input — the raw circular text fed into the pipeline"],
      ["circular_id", "str", "Module 1 — e.g. SEBI/HO/IMD/2024/053"],
      ["vanilla_summary", "str", "Module 1 — plain-English translation of the circular"],
      ["impact_triggers", "List[Dict]", "Module 1 — structured list of regulatory changes"],
      ["affected_clients", "List[Dict]", "Modules 2\u20134 — progressively enriched per-client records"],
      ["mfd_commission_delta", "Dict", "Module 3 — circular-derived commission impact summary"],
      ["action_cards", "List[Dict]", "Module 4 — final dashboard payload with all messages"],
      ["human_approval_status", "bool", "HITL — True = approved, False = revision needed"],
      ["processing_errors", "List[str]", "All nodes — accumulated error log for diagnostics"],
    ]
  ),
  spacer(200),
);

// ── 7. HUMAN-IN-THE-LOOP ──────────────────────────────────────────────────────
children.push(
  h1("7. Human-in-the-Loop Design"),
  divider(),
  body(
    "A core design requirement is that no client communications are ever sent without explicit " +
    "MFD approval. This is implemented using LangGraph\u2019s native interrupt mechanism."
  ),
  spacer(80),

  h2("Mechanism"),
  bullet("The graph is compiled with interrupt_before=[\"human_review\"]"),
  bullet("After the Dispatcher completes, LangGraph freezes execution and returns control to the caller"),
  bullet("The MFD reviews the full Action Card output in the terminal (or a future dashboard UI)"),
  bullet("The caller resumes the graph on the same thread_id with the approval decision"),
  bullet("MemorySaver preserves the complete state between the two invoke() calls in RAM"),
  spacer(80),

  h2("Routing Logic"),
  code("if human_approval_status == True:"),
  code("    route \u2192 END  (pipeline complete)"),
  code("if human_approval_status == False:"),
  code("    route \u2192 stage_dispatch  (Dispatcher re-runs, new messages generated)"),
  spacer(80),

  body(
    "This design means the MFD is always the final decision-maker before any client-facing " +
    "action is taken. The agent does the analytical heavy lifting; the human retains full " +
    "control over what actually goes out."
  ),
  spacer(200),
);

// ── 8. KEY ENGINEERING DECISIONS ───────────────────────────────────────────────
children.push(
  h1("8. Key Engineering Decisions"),
  divider(),

  makeTable(
    [3000, 3013, 3013],
    ["Decision", "Alternative Considered", "Why This Approach Won"],
    [
      ["LangGraph over standard LangChain", "Sequential LLM chain", "State persistence across nodes; native HITL interrupt; conditional routing without custom orchestration code"],
      ["Circular-driven tax analysis", "Hardcoded LTCG/STCG rates", "Hardcoded rates produce incorrect output for circulars that cause no tax events — fundamental correctness issue"],
      ["Rule-based Next Best Action", "LLM call per client", "NBA is deterministic from the trigger analysis already performed; removes 403 redundant API calls"],
      ["Batched dispatcher (15/call)", "1 LLM call per client", "Reduced 403 blocking calls to ~27; no quality loss; JSON batch response with fallback templates"],
      ["1 Groq call for trigger analysis", "Per-client LLM analysis", "Trigger analysis is circular-level, not client-level; applying it to clients is O(n) pure Python"],
      ["MemorySaver checkpointer", "External DB / Redis", "In-memory is sufficient for demo; swappable to SqliteSaver or RedisSaver for production"],
      ["TypedDict for GraphState", "Pydantic BaseModel", "LangGraph merges partial dicts natively; TypedDict has zero runtime overhead vs Pydantic validation"],
    ]
  ),
  spacer(200),
);

// ── 9. MOCK DATABASE ARCHITECTURE ─────────────────────────────────────────────
children.push(
  h1("9. Mock Database Architecture"),
  divider(),
  body(
    "The portfolio database simulates a realistic MFD book of business. It is generated " +
    "deterministically using random.seed(42), ensuring identical data across every run."
  ),
  spacer(80),

  h2("Database Specification"),
  makeTable(
    [3200, 5826],
    ["Property", "Detail"],
    [
      ["Total clients", "650"],
      ["Holdings per client", "1\u20136 fund positions (randomly sampled)"],
      ["Fund categories", "12: Small Cap, Mid Cap, Large Cap, ELSS, Liquid, Short Duration Debt, Corporate Bond, Flexi Cap, Multi Cap, Index Fund, International Fund, Gold Fund"],
      ["Total funds in universe", "26 funds with real names and ISINs"],
      ["Holding periods", "90 days to 2,190 days (3 months to 6 years)"],
      ["Investment amounts", "10,000 to 50,00,000 INR across 9 buckets"],
      ["Current value range", "0.65x to 2.8x of invested amount"],
      ["Nomination linked", "70% yes / 30% no"],
      ["KYC status", "85% verified / 15% pending"],
      ["Tax brackets", "30% (50%), 20% (30%), 5% (20%)"],
      ["Index structures", "Category index (O(1) category lookup), ID index (O(1) client lookup)"],
    ]
  ),
  spacer(200),
);

// ── 10. CHALLENGES & SOLUTIONS ─────────────────────────────────────────────────
children.push(
  h1("10. Challenges & Solutions"),
  divider(),

  makeTable(
    [3200, 5826],
    ["Challenge", "Solution"],
    [
      ["Pipeline stalling at 403 sequential LLM calls", "Redesigned Dispatcher to batch 15 clients per call; moved NBA generation to rule-based (0 LLM calls)"],
      ["Hardcoded tax math producing wrong output for non-tax circulars", "Complete Benefit Engine redesign: 1 LLM call analyzes triggers for tax relevance; tax section only appears if circular actually causes a tax event"],
      ["API key not loading from .env in node files", "Explicit load_dotenv(Path(__file__).parents[2] / '.env', override=True) in each node file with absolute path resolution"],
      ["Deprecated google-generativeai SDK", "Migrated to google-genai (new official SDK) immediately upon FutureWarning detection"],
      ["LLM returning JSON wrapped in markdown fences", "Regex stripping of ``` and ```json prefixes before json.loads(), with fallback template on parse failure"],
      ["IndexError on empty action_cards list", "Guarded with: cards[0] if cards else {} pattern throughout"],
      ["commission_delta type mismatch after redesign (float vs dict)", "Updated state.py TypedDict, dispatcher.py assembly, and main.py display function consistently"],
    ]
  ),
  spacer(200),
);

// ── 11. DATA FLOW SUMMARY ──────────────────────────────────────────────────────
children.push(
  h1("11. End-to-End Data Flow"),
  divider(),
  body("The complete journey of data through the system for the demo circular (SEBI/HO/IMD/2024/053):"),
  spacer(80),

  makeTable(
    [500, 2200, 2200, 4126],
    ["#", "Stage", "Input", "Output"],
    [
      ["1", "main.py", "SAMPLE_CIRCULAR text string", "Initial GraphState, graph invocation"],
      ["2", "Jargon-Cutter", "Raw circular text (5 sections)", "Vanilla summary + 2 impact triggers (T001: TER, T002: Nomination)"],
      ["3", "Book Auditor", "2 triggers with client_filter specs", "403 affected clients with holdings, exposure %, reasons"],
      ["4", "Benefit Engine", "403 clients + 2 triggers + summary", "Tax: No (TER/nomination \u2192 no forced exit) | Commission: Yes (actual TER %s)"],
      ["5", "Dispatcher", "403 enriched clients", "403 personalised emails in ~27 API calls | 1 Action Card assembled"],
      ["6", "HITL Pause", "Action Card snapshot", "MFD reviews 3 sample messages + metrics in terminal"],
      ["7", "Resume", "human_approval_status = True", "Graph routes to END | sentinel_output.json written"],
    ]
  ),
  spacer(200),
);

// ── 12. RESULTS ────────────────────────────────────────────────────────────────
children.push(
  h1("12. Results & Impact"),
  divider(),

  makeTable(
    [4000, 5026],
    ["Dimension", "Outcome"],
    [
      ["Workflow automation", "Full 4-step compliance workflow (read \u2192 audit \u2192 analyse \u2192 draft) completed autonomously"],
      ["Portfolio coverage", "All 650 client portfolios scanned in a single pipeline run"],
      ["Personalisation", "Every client message references their actual fund names, exposure amounts, and the specific regulatory change affecting them"],
      ["Tax accuracy", "Tax implications surfaced only when the circular actually causes them \u2014 not by default assumption"],
      ["Commission transparency", "Only actual circular figures used; explicitly flagged when the circular does not specify exact numbers"],
      ["Human control", "Zero client-facing output without explicit MFD approval via the HITL interrupt"],
      ["Fiduciary integrity", "System never suggests fund switches or portfolio churn to recover lost commission \u2014 enforced at prompt and logic level"],
      ["API efficiency", "~28 LLM calls for 403 clients vs 800+ in naive implementation"],
    ]
  ),
  spacer(200),
);

// ── 13. FUTURE ENHANCEMENTS ────────────────────────────────────────────────────
children.push(
  h1("13. Future Enhancements"),
  divider(),

  bullet("PDF ingestion pipeline — replace hardcoded SAMPLE_CIRCULAR with live PDF upload and text extraction (PyMuPDF / pdfplumber)"),
  bullet("Real MFD database integration — connect to BSE StarMF, MFCentral, or AMC APIs instead of mock data"),
  bullet("Web dashboard — React/Next.js UI for Action Card review, one-click client message approval, and dispatch via email/WhatsApp"),
  bullet("Persistent checkpointing — swap MemorySaver for SqliteSaver or RedisSaver for production-grade state durability"),
  bullet("Circular monitoring — scheduled agent polls SEBI and AMFI websites for new circulars and triggers the pipeline automatically"),
  bullet("Multi-circular batching — process multiple circulars in parallel using LangGraph\u2019s async invoke"),
  bullet("Audit trail — every agent decision, client impact assessment, and MFD approval logged immutably for compliance records"),
  bullet("Feedback loop — MFD edits to draft messages used to fine-tune future message quality"),
  spacer(200),
);

// ── 14. FILE STRUCTURE ─────────────────────────────────────────────────────────
children.push(
  h1("14. Project File Structure"),
  divider(),
  code("Circular/"),
  code("  main.py                      # Entry point, HITL loop, output display"),
  code("  requirements.txt             # langgraph, groq, pydantic, python-dotenv"),
  code("  architecture.md              # Mermaid.js state machine diagram"),
  code("  sentinel_output.json         # Full pipeline output dump"),
  code("  .env                         # GROQ_API_KEY (not committed)"),
  code(""),
  code("  sentinel/"),
  code("    state.py                   # GraphState TypedDict schema"),
  code("    graph.py                   # LangGraph assembly, edges, HITL, checkpointer"),
  code("    __init__.py"),
  code("    nodes/"),
  code("      jargon_cutter.py         # Module 1: NLP ingestion + trigger extraction"),
  code("      book_auditor.py          # Module 2: Portfolio cross-check (0 LLM calls)"),
  code("      benefit_engine.py        # Module 3: Circular-driven tax + commission"),
  code("      dispatcher.py            # Module 4: Batched message drafting"),
  code("      __init__.py"),
  code(""),
  code("  mock_data/"),
  code("    portfolio_db.py            # 650-client MFD book, 12 categories, real ISINs"),
  code("    __init__.py"),
  spacer(200),

  new Paragraph({ children: [new PageBreak()] }),

  // Final callout
  new Paragraph({ children: [new TextRun("")], spacing: { before: 1200 } }),
  new Paragraph({
    children: [new TextRun({ text: "Built end-to-end with LangGraph + Groq + Python", font: "Arial", size: 24, color: BLUE, italics: true })],
    alignment: AlignmentType.CENTER,
    spacing: { before: 0, after: 80 },
  }),
  new Paragraph({
    children: [new TextRun({ text: "Agentic Regulatory Sentinel v1.0  \u00B7  April 2026", font: "Arial", size: 20, color: MIDGRAY })],
    alignment: AlignmentType.CENTER,
  }),
);

// ══════════════════════════════════════════════════════════════════════════
// BUILD DOCUMENT
// ══════════════════════════════════════════════════════════════════════════

const doc = new Document({
  numbering: {
    config: [
      {
        reference: "bullets",
        levels: [{
          level: 0, format: LevelFormat.BULLET, text: "\u2022",
          alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 560, hanging: 280 } } },
        }],
      },
    ],
  },
  styles: {
    default: {
      document: { run: { font: "Arial", size: 22, color: DARKGRAY } },
    },
    paragraphStyles: [
      {
        id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 36, bold: true, font: "Arial", color: NAVY },
        paragraph: { spacing: { before: 400, after: 160 }, outlineLevel: 0 },
      },
      {
        id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 26, bold: true, font: "Arial", color: BLUE },
        paragraph: { spacing: { before: 280, after: 120 }, outlineLevel: 1 },
      },
      {
        id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 22, bold: true, font: "Arial", color: NAVY },
        paragraph: { spacing: { before: 200, after: 80 }, outlineLevel: 2 },
      },
    ],
  },
  sections: [{
    properties: {
      page: {
        size: { width: 11906, height: 16838 },
        margin: { top: 1080, right: 1080, bottom: 1080, left: 1080, header: 600, footer: 600 },
      },
    },
    headers: {
      default: new Header({
        children: [
          new Paragraph({
            children: [
              new TextRun({ text: "Agentic Regulatory Sentinel v1.0", font: "Arial", size: 18, color: BLUE, bold: true }),
              new TextRun({ text: "\tTechnical Project Report", font: "Arial", size: 18, color: MIDGRAY }),
            ],
            tabStops: [{ type: TabStopType.RIGHT, position: TabStopPosition.MAX }],
            border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: LIGHTBLUE, space: 1 } },
          }),
        ],
      }),
    },
    footers: {
      default: new Footer({
        children: [
          new Paragraph({
            children: [
              new TextRun({ text: "Confidential \u00B7 Interview Showcase", font: "Arial", size: 16, color: MIDGRAY }),
              new TextRun({ text: "\tPage ", font: "Arial", size: 16, color: MIDGRAY }),
              new TextRun({ children: [PageNumber.CURRENT], font: "Arial", size: 16, color: BLUE }),
            ],
            tabStops: [{ type: TabStopType.RIGHT, position: TabStopPosition.MAX }],
            border: { top: { style: BorderStyle.SINGLE, size: 4, color: LIGHTBLUE, space: 1 } },
          }),
        ],
      }),
    },
    children,
  }],
});

const OUT = "C:\\Users\\shubh\\OneDrive\\Desktop\\Circular\\Agentic_Regulatory_Sentinel_Report.docx";
Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync(OUT, buf);
  console.log("Done:", OUT);
}).catch(e => { console.error(e); process.exit(1); });
