
# Economic Survey Practitioner Chat (PDF + XLSX + Supplements + Analytics + Google Login)

**Version:** v1.2 (Clean Consolidated)  
**Audience:** Fullstack Developer (Python + HTML/JS)  
**Primary Goal:** A “smart economics/finance practitioner” chat experience grounded in Survey + datasets + supplements  
**Ingestion:** One-time, offline, developer-run (no runtime parsing/compute)  
**Runtime:** Retrieval + response generation only  
**Frontend:** 2 user-facing pages (Summary + Chat)  
**Authentication:** Google Login (usage tracking only, no PII storage)  
**Analytics:** Track what users ask + concerns + optimism/pessimism (offline labeling)

---

## 1) Product Overview

### 1.1 What we are building
A web application that lets users:
1. Read a **3–5 minute briefing summary** of the Economic Survey (plus context)
2. Chat with an assistant that answers like an **experienced economics/finance practitioner**
3. See **evidence citations** for every factual claim (PDF + XLSX + supplements)

### 1.2 Core constraints (non-negotiable)
- **No runtime ingestion** of PDF or XLSX.
- All parsing, table detection, normalization, embeddings, summaries, and derived metrics must be computed **offline once**.
- Runtime only:
  - retrieves precomputed artifacts
  - expands cross-links via graph edges
  - generates final answer text
  - logs user interactions

### 1.3 Corpus scope
The system corpus includes:
- **Economic Survey PDFs** (whole volume or chapter-wise PDFs)
- **Economic Survey XLSX datasets** (multi-sheet, multi-table, multi-panel)
- **Supplementary reports** (PDF/DOCX/HTML exports) for additional context

---

## 2) User Experience (Frontend)

### 2.1 Only two user-facing pages
1. **Summary page:** `/summary/{corpus_id}`
2. **Chat page:** `/chat/{corpus_id}`

No user upload UI.

### 2.2 Summary page (3–5 minute read)
**Purpose:** A briefing note, not a long report.

**Must render:**
- Corpus title + year
- **Topline bullets** (5–8 bullets)
- **Topic briefs** (expand/collapse):
  - Growth & Demand
  - Inflation & Rates
  - Investment & Capex
  - Fiscal
  - External Sector
  - Labour & Welfare
  - Financial Conditions (optional)
- **Key numbers** (4–10 chips)
- Evidence drawer (modal or right-side panel)

**Evidence drawer supports:**
- **PDF evidence:** label + page range + snippet
- **Dataset evidence:** workbook + sheet + A1 range + table preview (first 10 rows)
- **Supplement evidence:** document title + snippet

### 2.3 Chat page (ChatGPT-like)
**Required UI features**
- Chat transcript with user + assistant bubbles
- Streaming assistant output (SSE)
- Message input with enter-to-send
- Evidence panel for latest assistant response
- Toggle: **Show economic intuition** (on/off)

**UX rule**
- Assistant should NOT dump raw tables by default.
- It should summarize and offer: “Want the table slice / series?”

---

## 3) Authentication, Privacy & Usage Tracking (Google Login)

### 3.1 Why login exists
Google login is required **only** to:
- track usage during the **free access period**
- prevent abuse/spam
- allow aggregate analytics on usage and questions

### 3.2 Data minimization promise (mandatory)
The system must **not store any personal information** from Google.

**Do NOT store:**
- name
- email (plaintext)
- profile photo
- phone number
- address
- access tokens / refresh tokens (long-term)

**Store only:**
- A pseudonymous identifier computed at login:

```
user_pseudo_id = SHA256(google_sub + server_salt)
```

This enables stable tracking without storing identity.

### 3.3 OAuth method

Use Google OAuth2 OpenID Connect. Backend must validate:

- JWT signature
- issuer (iss)
- audience (aud)
- expiry (exp)
- extract sub

### 3.4 Session management

Use secure cookie sessions:

- HttpOnly
- Secure
- SameSite=Lax
- Session stores only: user_pseudo_id, session_id

### 3.5 UI disclosure (required)

Login page must display:
“Login is required only to track usage during the free access period. We do not store your name, email, or personal profile data.”

## 4) System Behavior (Practitioner-Grade Chat)
### 4.1 Required answer structure

Every assistant response must have:

- Answer (direct, practitioner tone)
- Why / mechanism (economic intuition, clearly labeled)
- Evidence (citations list)

### 4.2 Evidence rules (anti-hallucination)

Any numeric/statistical claim must cite evidence:

- PDF node OR dataset table OR indicator series OR supplement node
- Interpretation must not introduce new numbers.

### 4.3 Cross-link behavior

If retrieved evidence references a table / box / chart / chapter / dataset object, the system must include linked evidence via graph expansion.

## 5) Architecture
### 5.1 Offline ingestion (developer-run once)

Offline pipeline outputs:

- structured nodes (PDF + supplements)
- dataset tables (XLSX)
- indicator registry + series + derived metrics
- cross-link graph edges
- embeddings + keyword index
- briefing summaries + claim cards

### 5.2 Runtime (online)

Runtime does:

- retrieval (FTS + vector)
- graph expansion
- response generation
- logging and analytics events
- No parsing, no table extraction, no embedding generation at runtime.

## 6) Technology Stack
### 6.1 Backend

- Python 3.11+
- FastAPI
- Postgres 15+
- pgvector
- Optional Redis (not required)

### 6.2 Offline ingestion libraries

- PDF parsing: PyMuPDF (fitz)
- XLSX parsing: openpyxl
- Optional: Camelot (PDF tables only if needed)

### 6.3 Frontend

- HTML + CSS + vanilla JS
- Server-Sent Events for streaming

## 7) Data Model (Postgres)
### 7.1 Core entities

- Corpus: a collection (Survey + supplements + datasets)
- Document: a PDF report (survey chapter/volume or supplement)
- Node: a unit of evidence (section, paragraph, box, dataset table, etc.)
- Edge: relationship between nodes (contains, refers_to, supports)

### 7.2 Required database tables

#### Corpora

- `corpora(id, name, description, created_at)`

#### Documents

- `documents(id, corpus_id, title, year, volume, role, created_at)`
  - `role ∈ {primary, supplement}`

#### Nodes

- `nodes(id, document_id, node_type, label, title, text, page_start, page_end, metadata)`

#### Edges

- `edges(id, document_id, src_node_id, rel_type, dst_node_id, confidence, evidence)`
  - `rel_type ∈ {contains, refers_to, supports}`

#### Dataset tables (XLSX)

- `data_files(id, corpus_id, filename, path, created_at)`
- `data_sheets(id, file_id, sheet_name, sheet_index, metadata)`
- `data_tables(id, file_id, sheet_id, title, table_name, range_a1, header_rows, index_cols, units, notes, table_json, table_long, tags, confidence)`

#### Indicators

- `indicators(id, corpus_id, name, aliases, topic, unit, freq, geo_level, definition, provenance)`
- `indicator_series(id, indicator_id, geo_key, time_start, time_end, points, derived_views, provenance)`

#### Summaries and claims

- `topic_briefs(id, corpus_id, topic, bullets, key_numbers, linked_node_ids, linked_series_ids)`
- `claim_cards(id, corpus_id, topic, claim_text, explanation, evidence_node_ids, evidence_series_ids, confidence)`

#### Search

- `search_index(document_id, node_id, raw_text, tsv)`
- `embeddings(document_id, node_id, embedded_text, embedding)`

#### Analytics

- `conversations(id, corpus_id, created_at, user_pseudo_id, session_metadata)`
- `messages(id, conversation_id, role, content, created_at, metadata)`
- `retrieval_events(id, conversation_id, message_id, retrieved_node_ids, retrieved_series_ids, used_evidence, latency_ms, created_at)`
- `message_labels(message_id, topics, entities, intent, sentiment, concerns, confidence, label_version, created_at)`

#### Optional rollups

- `daily_insights(date, total_questions, top_topics, top_concerns, sentiment_mix, notable_questions, created_at)`
- `topic_clusters(cluster_id, date_range, topic, summary, example_message_ids, created_at)`

## 8) Offline Ingestion Pipeline (One-Time)
### 8.1 Inputs

- Survey PDFs (whole volume preferred)
- Survey chapter PDFs (allowed)
- Survey XLSX datasets directory
- Supplementary reports (PDF/DOCX/HTML)

### 8.2 Output artifacts (must exist before runtime)

- nodes + edges
- dataset tables + long-form records
- indicator registry + series + derived metrics
- topic briefs + claim cards
- embeddings + keyword index

### 8.3 PDF ingestion (Survey + Supplements)
 Steps:
  Extract text blocks by page (born-digital)
  Detect structure:
   - chapter → section → paragraph
   - Detect objects:
   - tables, boxes, charts
 Build reference registry:
  Table I.2a, Box I.2, Chart I.21, Chapter 4

 Create edges:
  - contains, refers_to, supports
 Index:
  - store in FTS + embeddings
 Cross-chapter ingestion rule
   If ingesting chapter PDFs separately, they must share the same corpus and a resolver pass must run after all chapters are ingested.

### 8.4 XLSX ingestion (multi-sheet, multi-table, multi-panel)
 This must work for both:
  - PACK workbooks (many sheets like tabchart)
 BIG_TABLE workbooks (single huge table like tab1.1)

#### 8.4.1 Workbook classification
  PACK if sheet_count ≥ 5 OR sheet names contain Chart/Table
  BIG_TABLE if used-range is huge and col A is mostly time keys
  Else PACK

#### 8.4.2 PACK sheet detection (panel splitting mandatory)
 Each sheet:
  - detect title row (contains “Chart” or “Table”)
  - detect header row
  - extract region until blank/Source/Note
  - split panels if a mid-sheet label like “Growth”/“Inflation” exists
  - store each panel as its own data_tables row

#### 8.4.3 BIG_TABLE detection
 detect title row
 detect multi-row header
 detect time rows (FY pattern)
 extract full region
 store as one table

#### 8.4.4 Normalization to long format
 Convert each table into table_long.records:
  - time, geo, indicator, measure, value, unit, provenance

#### 8.4.5 Indicator registry build
 From all table_long:
  - group into indicators + series
  - compute derived metrics offline:
  - YoY
  - CAGR windows (3/5/10)
  - ranks (if applicable)

### 8.5 PDF ↔ XLSX linking (offline)
 Required deterministic linking:
  - If PDF references “Chart I.x” and XLSX has matching chart sheet → link via supports edge.
  - Same for “Table I.x”.
 Optional semantic linking:
  - for each Survey section, attach 1–3 dataset tables that best support it.

### 8.6 Precompute Topic Briefs (offline)
 Generate topic briefs:
  - 3–8 bullets per topic
  - 1–3 key numbers per topic with citations
  - Store in topic_briefs.

### 8.7 Precompute Claim Cards (offline)

Generate 20–50 claim cards per topic:
  - claim_text: one-sentence claim
  - explanation: practitioner tone
  - evidence: node_ids and/or series_ids
  - Hard rule: every claim card must have ≥1 evidence item.

## 9) Runtime Retrieval & Response (No Compute)
### 9.1 Query classification (deterministic)

If user query contains:

- trend, series, years, CAGR, YoY, compare, vs, rank, top, bottom → treat as a data query and prioritize indicator_series.

Else:

- treat as a narrative query and prioritize claim_cards + PDF nodes.

### 9.2 Retrieval sources priority

- claim_cards
- topic_briefs
- indicator_series
- PDF nodes
- dataset_table nodes
- supplement nodes (unless explicitly requested)

### 9.3 Graph expansion

For retrieved nodes:

- follow refers_to edges depth 1
- follow supports edges depth 1
- Include those linked objects in the context pack.

### 9.4 Context Pack Rules (Token Budget + Category Quotas)

 Goal: Build a deterministic, evidence-grounded context pack that fits within a fixed token budget while preserving cross-linkages and maintaining “practitioner” answer quality.

#### 9.4.1 Inputs

 user_question
 corpus_id
 optional conversation_history (last 3–6 turns)
 retrieval candidates from:
  - claim_cards
  - topic_briefs
  - indicator_series
  - PDF nodes (paragraph/box/table/chart)
  - dataset_table nodes
  - supplement nodes

#### 9.4.2 Output

 A context pack object sent to the LLM containing only selected items and truncated previews/snippets.

#### 9.4.3 Global token budget

 The context pack must not exceed:
  - CONTEXT_BUDGET_TOKENS (configurable)
  - Default: 10,000 tokens

#### 9.4.4 Category token quotas (default)

 Allocate the global budget into deterministic category quotas:
  - Conversation memory: 500 tokens
  - Claim cards / topic briefs: 1,500 tokens
  - Narrative evidence (Survey PDF + supplements): 4,000 tokens
  - Data evidence (dataset tables + indicator series): 4,000 tokens
 If one category quota is under-used, unused tokens may be reallocated to other categories, except where restricted below.

#### 9.4.5 Must-include rules (highest priority)

 Always include the following even if it forces dropping lower-priority items:
  - Any object explicitly referenced in the question (e.g., “Table I.2a”, “Box I.2”, “Chart I.21”, “Chapter 4”)
  - Top 1 matching claim card (if any exist)
  - If query is data or mixed: top 1 matching indicator series

#### 9.4.6 Cross-link preservation (graph expansion)

 For the top-ranked narrative nodes and claim cards, include linked objects via graph edges:
  - follow refers_to edges depth 1
  - follow supports edges depth 1
 Linked objects are “sticky” and should be included unless they exceed budget and are not explicitly requested.

#### 9.4.7 Selection ranking (deterministic)

 For each candidate item compute:
  - value_score = retrieval_score + boosts:
  - +5 if explicitly mentioned in question
  - +2 if from primary Survey document
  - +1 if linked via graph expansion
  - -2 if supplement and not explicitly requested
  - token_cost = estimated tokens of the snippet/preview to include
 Select items in descending order of:
  - value_score / token_cost

 Fill each category quota using this ranking rule.

#### 9.4.8 Supplement restriction (default)

 Unless user explicitly requests supplementary sources:
  - supplement snippets must not exceed 25% of the narrative quota i.e., max 1,000 tokens out of 4,000 by default

#### 9.4.9 Included content per item (truncate rules)

 To control token usage:
  - Claim card: include claim_text, explanation, evidence IDs (max ~900 tokens per card)
  - PDF paragraph/box: include label + pages + snippet (max ~1,200 characters)
  - PDF table/chart: include caption + surrounding text (max ~800 characters)

 Dataset table: include file/sheet/range + preview (max 10 rows × 10 cols)
 Indicator series: include a summary card only:
  - last value + last time
  - latest YoY and latest CAGR (if present)
  - Return full series points only if user explicitly asks “show me the series”.

#### 9.4.10 Budget enforcement (drop order)

 If the pack exceeds the global budget, remove items in this order:
  - supplement snippets (unless explicitly requested)
  - extra dataset tables beyond the first 1–2
  - extra narrative nodes beyond the top-ranked ones
  - extra indicator series beyond the top 1–2
  - Never drop explicitly referenced objects.

### 9.5 Response format (strict)

Backend must return JSON:

```json
{
  "answer": "...",
  "intuition": "...",
  "evidence": [...],
  "followups": ["..."]
}
```

## 10) Prompting (Strict Practitioner Style)
### 10.1 System prompt rules

- speak like an economist/finance practitioner
- separate Answer / Why / Evidence
- no uncited numbers
- no table dumping unless user asks
- cite sources with labels + provenance

### 10.2 Output schema enforcement

 Backend must validate the JSON response schema.
 If invalid, retry once with “fix JSON only”.

## 11) Backend API Spec
### 11.1 Auth

- `GET /auth/login` → redirects to Google
- `GET /auth/callback` → validates token, sets session cookie
- `POST /auth/logout` → clears session

### 11.2 Briefing

`GET /api/corpus/{corpus_id}/briefing`

### 11.3 Chat

`POST /api/chat`

Request body:

```json
{
  "corpus_id": "...",
  "conversation_id": "...",
  "message": "..."
}
```

`GET /api/chat/stream/{conversation_id}` (SSE)

### 11.4 Evidence

These endpoints are used by the frontend Evidence Drawer / Evidence Panel to render citations and previews.

- `GET /api/evidence/node/{node_id}` - Returns a single evidence node (PDF paragraph/box/table/chart snippet).
- `GET /api/evidence/table/{table_id}` - Returns a dataset table preview (first 10 rows × first 10 columns), plus metadata:
  - workbook filename
  - sheet name
  - A1 range
  - notes/units
- `GET /api/evidence/series/{series_id}` - Returns an indicator series summary card, plus derived views:
  - last value + last time
  - latest YoY (if present)
  - latest CAGR windows (if present)

### 11.5 Admin analytics (API only, no UI required)

These endpoints provide aggregated usage analytics for administrators.

`GET /api/admin/insights?start=YYYY-MM-DD&end=YYYY-MM-DD`

Returns:

- total questions
- top topics
- top concerns
- sentiment mix (optimistic/neutral/pessimistic/mixed)
- notable questions

`GET /api/admin/top_questions?start=YYYY-MM-DD&end=YYYY-MM-DD`

Returns:

- most frequent user questions (normalized)
- representative examples
- associated topics
- Access control requirement: Admin endpoints must require an admin flag in server config (no public access).

## 12) Analytics & Insights (Offline, Not Runtime)
### 12.1 Runtime logging (required)

On every user message:

- store messages
- store retrieval_events including:
  - retrieved node IDs
  - retrieved series IDs
  - used evidence objects (final citations)
  - latency (ms)

### 12.2 Offline labeling job

A daily offline job must classify messages into:

- topics
- entities
- intent: question / clarification / challenge / request / feedback
- sentiment: optimistic / neutral / pessimistic / mixed
- concerns list

Store results in message_labels.
### 12.3 Offline clustering job (weekly)

A weekly offline job must:

- embed user questions
- cluster them into themes
- store cluster summaries in topic_clusters

### 12.4 Insight metrics

Compute and expose:

- topic frequency
- concern frequency
- sentiment mix
- most cited evidence nodes
- questions with low evidence coverage (improvement backlog)

## 13) Security & Governance
### 13.1 PII policy (mandatory)
 Do not store Google personal info.
 Store only pseudonymous id (user_pseudo_id).

### 13.2 Retention

- keep raw messages for configurable duration (default 180 days)
- keep aggregates longer

### 13.3 Auditability

Store retrieval_events to trace:

- what evidence was retrieved
- what evidence was used
- what sources influenced the final answer

## 14) Developer Style Guides (Guardrails)
### 14.1 Python

- Python 3.11
- black + ruff
- pydantic models for all API payloads
- ingestion scripts must be idempotent

### 14.2 Table guardrails (XLSX)

Handle:

- multi-row headers (cap at 6)
- panel splitting on repeated headers
- Source/Note termination
- missing numeric cells ("NA", "-", "…") → null
- percent parsing ("5.2%" → 5.2)

### 14.3 Determinism

- No "tune later" logic.
- All thresholds fixed in code and logged.

## 15) Acceptance Tests (Must Pass)
### 15.1 XLSX detection

- Multi-panel sheet must split into two tables (Growth vs Inflation) when present.
- Big-table workbook must detect FY time column correctly.

### 15.2 Linking

"Chart I.x" must link PDF ↔ XLSX when both exist.

### 15.3 Chat quality

- Answers must be structured Answer/Why/Evidence.
- No uncited numeric claims.

### 15.4 Privacy

- DB must not store plaintext email/name.
- Only user_pseudo_id stored.

## 16) Deployment
### 16.1 Environments

- local dev: docker-compose
- production: containerized

### 16.2 Required env vars

- DB_URL
- GOOGLE_CLIENT_ID
- GOOGLE_CLIENT_SECRET
- SESSION_SECRET
- SERVER_SALT (for pseudonymous hashing)
- LLM_API_KEY
- EMBEDDING_MODEL_ID

## 17) Content Folder Contract (Required)

 This project relies on one-time offline ingestion. Therefore, the Content/ folder structure and naming conventions are a hard contract.
 If these rules are violated, ingestion must fail fast with a clear error message.

### 17.1 Required Folder Structure

All ingestion must assume the following directory layout:

```
Content/
├── Report/
│   ├── survey_volume_1.pdf
│   ├── survey_volume_2.pdf
│   └── chapters/
│       ├── echap01.pdf
│       ├── echap02.pdf
│       └── ...
│
├── Charts_and_Tables/
│   ├── tabchart1.xlsx
│   ├── tabchart2.xlsx
│   └── ...
│
├── Statistical_Index/
│   ├── tab1.1.xlsx
│   ├── tab1.2.xlsx
│   ├── tab6.2b.xlsx
│   └── ...
│
└── Supplementary_reports/
    ├── *.pdf
    ├── *.xlsx
    └── *.html
```

### 17.2 Naming Rules (Hard Rules)

All file patterns below are **required**. Behavior on mismatch:

- **Default mode (skip):** Files not matching patterns are logged as warnings and skipped silently. Ingestion continues.
- **Strict mode (fail):** Files not matching patterns cause the entire ingestion to fail with an error. Set via `--strict` flag.

Recommended: Use strict mode for production, skip mode for development.

#### 17.2.1 Survey chapter PDFs

Pattern: `echapNN.pdf`

NN must be 2 digits

Examples:

- echap01.pdf
- echap12.pdf

#### 17.2.2 Charts and tables workbooks

Pattern: `tabchartN.xlsx`

N must be an integer

Examples:

- tabchart1.xlsx
- tabchart15.xlsx
 
#### 17.2.3 Statistical Index workbooks

Pattern: `tabX.Y.xlsx`

X = chapter number
Y = table number (may include suffix letters)

Examples:

- tab1.1.xlsx
- tab6.2b.xlsx
- tab8.9a.xlsx
### 17.3 File Type Rules
#### 17.3.1 Allowed file types by folder

- `Content/Report/`: .pdf (preferred), .html (fallback only)
- `Content/Charts_and_Tables/`: .xlsx only
- `Content/Statistical_Index/`: .xlsx only
- `Content/Supplementary_reports/`: .pdf, .xlsx, .html
### 17.4 Provenance Rules (Mandatory)

Every ingested object must store:

- source_path (relative to Content/)
- source_filename
- source_folder (Report|Charts_and_Tables|Statistical_Index|Supplementary_reports)
- document_role (primary|supplement)
- ingested_at
- corpus_id

Role assignment:

- `Content/Report/*` → document_role=primary
- `Content/Supplementary_reports/*` → document_role=supplement

### 17.5 Corpus Ingestion Command Contract (Required)

```bash
python -m ingestion.run_all \
  --corpus_id <uuid> \
  --content_root ./Content
```

Runner order:

- Ingest Survey PDFs (Report/)
- Ingest XLSX (Charts_and_Tables/)
- Ingest XLSX (Statistical_Index/)
- Ingest supplements (Supplementary_reports/)
- Resolver pass (cross-links + references)
- Build embeddings + FTS
- Build indicators + derived metrics
- Build topic briefs + claim cards

**Stop Condition:** Runtime must never ingest or parse content.

---

*End of Spec Doc v1.2*