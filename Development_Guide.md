AI-Led Development Guide (VS Code Chat) — Economic Survey Practitioner Chat v1.2
1) Prime directive

Build exactly what the spec says with no interpretation changes:

One-time ingestion only (PDF/XLSX/supplements)

Runtime does retrieval + response only

Two user pages only: Summary and Chat

Google login: usage tracking only, store no PII

Practitioner chat responses: Answer + Why + Evidence

Analytics: log interactions; insights computed offline

If something is ambiguous: assume deterministic defaults and log warnings rather than adding new features.

2) Ground rules for code generation

When generating code:

Prefer simple, explicit, deterministic implementations over clever abstractions.

No runtime background jobs except SSE streaming.

Every endpoint must have:

request/response pydantic models

clear error handling

All ingestion steps must be idempotent (upsert / source_hash).

Never store Google email/name; only store user_pseudo_id = SHA256(sub + SERVER_SALT).

3) Repo structure (fixed)

Use this exact structure:

survey-practitioner-chat/
  backend/
  ingestion/
  frontend/
  docker-compose.yml
  README.md


Do not introduce additional folders unless absolutely necessary.

4) Build order (AI should follow this)
Phase 1 — Database + Models

Goal: compile/run migrations and launch API.

Tasks

Create migrations.sql exactly per schema.

Create SQLAlchemy models matching tables (no extra fields).

Create DB engine + session manager.

Acceptance

docker-compose up boots Postgres + API

API can connect to DB

Phase 2 — Google Login (minimal + safe)

Goal: user sessions without storing PII.

Tasks

Implement /auth/login, /auth/callback, /auth/logout.

Validate OIDC ID token and extract sub.

Create user_pseudo_id = sha256(sub + SERVER_SALT) (store this only).

Create secure session cookie (HttpOnly, Secure, SameSite=Lax).

Acceptance

Logging in creates session

DB never stores email/name tokens

Session contains only pseudo id

Phase 3 — Offline ingestion (XLSX first)

Goal: ingest the two representative XLSX deterministically.

Tasks

Implement workbook classifier PACK vs BIG_TABLE.

Implement PACK detection with panel split.

Implement BIG_TABLE detection.

Normalize to table_json + table_long.

Create data_files, data_sheets, data_tables records.

Acceptance

tabchart1.xlsx sheet “Table I.1” produces 2 data_tables (Growth + Inflation panels).

tab1.1.xlsx produces 1 data_table with FY time detected.

All records have range_a1, table_json, table_long.

Phase 4 — Indicator registry + derived views (offline)

Goal: no runtime compute; series precomputed.

Tasks

Build indicators + indicator_series from table_long.

Compute derived_views offline: YoY, CAGR windows.

Acceptance

Series exist for key indicators with points + derived_views in DB.

Phase 5 — PDF ingestion (structure + refs)

Goal: nodes + edges + cross-links.

Tasks

Extract pages text with PyMuPDF.

Detect chapter/section/paragraph.

Detect objects (tables/boxes/charts) by caption patterns.

Extract references (Table/Box/Chart/Chapter) and create refers_to edges.

Create placeholders for missing chapters and resolve in a second pass.

Acceptance

Nodes exist for chapter/sections.

refers_to edges exist for “See Table/Box/Chapter”.

Phase 6 — Summaries + claim cards (offline)

Goal: practitioner feel.

Tasks

Generate topic_briefs (bullets + key numbers + citations).

Generate claim_cards (claim + explanation + evidence lists).

Store in DB.

Acceptance

Summary endpoint can render a briefing from precomputed tables.

Phase 7 — Retrieval + chat runtime

Goal: fast and grounded.

Tasks

Implement retrieval across claim_cards, topic_briefs, indicator_series, nodes, data_tables.

Graph expansion on refers_to and supports.

Construct evidence pack.

Call LLM with strict JSON schema.

Stream response via SSE.

Acceptance

Chat returns JSON: answer/intuition/evidence/followups.

No uncited numbers.

Evidence drawer populates.

Phase 8 — Analytics logging + offline insights

Goal: measure what users ask + sentiment.

Tasks

Log conversations/messages/retrieval_events at runtime.

Offline job labels messages into message_labels.

Offline job clusters into topic_clusters.

Admin insights API returns aggregated stats.

Acceptance

Messages stored with pseudo id.

daily_insights can be generated offline.

5) Deterministic table handling rules (XLSX guardrails)

AI must code these exactly:

Header rows auto-detected by density, capped at 6.

Source/Note rows terminate table and captured into notes.

“Growth/Inflation” mid-sheet blocks must split into separate panels.

Parse numbers:

commas removed

“NA”, “-”, “…” -> null

“(1.2)” -> -1.2

“5.2%” -> 5.2 (unit percent if missing)

If parsing uncertain: keep as string + reduce confidence.

6) Runtime retrieval rules (no compute)

Numeric queries prioritize indicator_series.

Narrative queries prioritize claim_cards then PDF nodes.

Supplements used only if:

explicitly asked OR

Survey evidence is insufficient.

Always label citations with source.

7) Response rules (must not drift)

AI must generate assistant responses that:

Have 3 labeled sections: Answer / Why / Evidence.

Every numeric claim maps to evidence item.

No table dumps unless user asks.

Backend must validate response against JSON schema; retry once if invalid.

8) Developer “prompt templates” for VS Code Chat

Use these copy/paste prompts to keep the AI on rails.

Prompt A — Generate DB + models

“Create migrations.sql and SQLAlchemy models for the schema in spec v1.2. No extra fields. Add indexes. Provide engine/session utilities.”

Prompt B — Implement Google Login safely

“Implement Google OIDC login with /auth/login and /auth/callback in FastAPI. Validate id token; store only user_pseudo_id=sha256(sub+SERVER_SALT). Secure cookie session.”

Prompt C — XLSX ingestion PACK+BIG_TABLE

“Implement openpyxl-based detectors for PACK and BIG_TABLE workbooks. Must split multi-panel sheets into separate data_tables. Output table_json and table_long exactly as defined.”

Prompt D — Build indicator_series and derived_views offline

“From data_tables.table_long, create indicators and indicator_series with derived_views (yoy, cagr windows). No runtime compute.”

Prompt E — Chat retrieval + SSE

“Implement retrieval pipeline and SSE chat streaming. Response must be strict JSON: answer/intuition/evidence/followups. Evidence list required. No uncited numbers.”

Prompt F — Analytics logging + labeling job

“Implement DB writes for conversations/messages/retrieval_events. Add offline label_messages.py to classify topics, concerns, sentiment into message_labels.”

9) “Stop conditions” (AI must not proceed past these failures)

If Google login stores email/name anywhere → stop and fix.

If chat emits a numeric claim without evidence → stop and fix.

If XLSX detector doesn’t split Table I.1 panels → stop and fix.

If runtime is parsing XLSX/PDF → stop and fix.

10) Definition of Done (DoD)

The build is done when:

Ingestion scripts run end-to-end once and populate DB.

Summary page shows 3–5 min briefing + citations.

Chat page streams practitioner answers with evidence.

Analytics tables populate; offline labeling produces sentiment/topic summaries.

No PII stored; only pseudonymous IDs.