# Implementation Plan for Economic Survey Practitioner Chat v1.2

Based on the spec and development guide, here's a comprehensive plan to build this system.

## 📋 Architecture Overview

**Backend Stack:**
- FastAPI (Python 3.11+)
- PostgreSQL 15+ with pgvector extension
- Google OAuth2 for authentication
- LLM API (OpenAI/Anthropic) for chat responses
- Server-Sent Events for streaming

**Frontend Stack:**
- Static HTML/CSS/vanilla JavaScript
- Deployed via Netlify (auto-deploy from GitHub)

**Infrastructure:**
- GCP for hosting (Cloud SQL, Cloud Run/Compute Engine)
- GitHub repository for version control and CI/CD trigger

---

## 🎯 Implementation Plan (10 Phases)

### **Phase 1: Database Setup & Models**
**Goal:** Working database with all tables and API skeleton

**Tasks:**
1. Create project structure
2. Create `migrations.sql` with all required tables in Spec v1.2, including search (search_index, embeddings), analytics (conversations, messages, retrieval_events, message_labels), and optional rollups (daily_insights, topic_clusters)
3. SQLAlchemy models for all entities
4. Database connection utilities
5. FastAPI app skeleton with health check

**Deliverables:**
- `docker-compose up` starts Postgres + API
- Health endpoint returns 200
- All tables created successfully

---

### **Phase 2: Google OAuth Authentication**
**Goal:** Secure login without storing PII

**Tasks:**
1. Implement OAuth2 flow endpoints
2. Validate ID token (signature, iss, aud, exp)
3. Generate `user_pseudo_id = SHA256(sub + SERVER_SALT)`
4. Secure session cookies (HttpOnly, Secure, SameSite=Lax)
5. Middleware for protected routes

**Deliverables:**
- User can log in via Google
- Database stores only `user_pseudo_id`
- Session persists across requests
- **Stop condition:** No email/name stored anywhere

---

### **Phase 3: XLSX Ingestion Pipeline**
**Goal:** Deterministic multi-table, multi-panel detection

**File Pattern Enforcement:**
- By default, files not matching naming patterns are skipped with warnings
- Use `--strict` flag to fail entire ingestion if any file violates patterns
- Recommended: strict mode for production, skip mode for development

**Tasks:**
1. Workbook classifier (PACK vs BIG_TABLE)
2. PACK detector with panel splitting logic
3. BIG_TABLE detector (FY time column detection)
4. Table normalization to `table_json` + `table_long`
5. Populate `data_files`, `data_sheets`, `data_tables`
6. Handle multi-row headers (cap at 6)
7. Parse numbers with rules (commas, NA, percentages, negatives)
8. Extract Source/Note rows

**Test cases:**
- `tabchart1.xlsx` "Table I.1" → 2 data_tables (Growth + Inflation)
- `tab1.1.xlsx` → 1 data_table with FY time column
- Verify `range_a1`, `table_json`, `table_long` populated

**Deliverables:**
- Idempotent ingestion script
- CLI: `python -m ingestion.xlsx_ingest <file_path> <corpus_id>`
- **Stop condition:** Panel split must work for Table I.1

---

### **Phase 4: Indicator Registry & Derived Metrics**
**Goal:** No runtime compute; all metrics precomputed

**Tasks:**
1. Build `indicators` table from `table_long` records
2. Group time series into `indicator_series`
3. Compute offline derived views (YoY, CAGR windows)
4. Store in `derived_views` JSON field
5. Create series summary cards

**Deliverables:**
- Script: `python -m ingestion.indicators <corpus_id>`
- Database has indicator_series with `points` + `derived_views`
- API endpoint: `GET /api/evidence/series/{series_id}` returns summary

---

### **Phase 5: PDF Ingestion & Cross-Linking**
**Goal:** Structured nodes with references

**Tasks:**
1. Extract text from PDF (PyMuPDF)
2. Detect structure (Chapter → Section → Paragraph)
3. Detect objects by caption patterns (Tables, Boxes, Charts)
4. Build reference registry (Table I.2a, Box I.2, Chart I.21)
5. Create edges with standardized rel_types: contains, refers_to, supports (ONLY these three; parent/child relationships represented via contains)
6. Cross-link PDF ↔ XLSX
7. Handle multi-chapter ingestion with resolver pass
8. Generate embeddings for nodes (offline, deterministic):
   - Use consistent `embedding_model_id` (e.g., text-embedding-3-large)
   - Embed constructed text: `title + " - " + node_label + " - " + snippet`
   - Store `source_hash` of embedded_text for reproducibility
   - Embeddings must have dimensionality matching model (e.g., 1536 for OpenAI)
9. Build FTS index
10. Classify documents: documents.role = 'primary' OR 'supplement'

**Deliverables:**
- Script: `python -m ingestion.pdf_ingest <pdf_path> <corpus_id>`
- Nodes exist for chapters/sections/paragraphs/objects
- Edges use ONLY rel_types: contains, refers_to, supports
- Embeddings generated offline with model_id + source_hash stored
- Supplement documents explicitly marked with role = 'supplement'
- **Stop condition:** "Chart I.x" must link PDF ↔ XLSX
- **Stop condition:** No embeddings generated at runtime

---

### **Phase 6: Summaries & Claim Cards**
**Goal:** Practitioner-quality briefings

**Tasks:**
1. Generate topic briefs (offline with LLM)
2. Generate claim cards (20-50 per topic)
3. Populate `topic_briefs` and `claim_cards` tables
4. Briefing API endpoint

**Deliverables:**
- Script: `python -m ingestion.summaries <corpus_id>`
- `GET /api/corpus/{corpus_id}/briefing` returns JSON
- **Stop condition:** Every claim card must have ≥1 evidence

---

### **Phase 7: Chat Retrieval & Streaming**
**Goal:** Fast, grounded practitioner responses

**Tasks:**
1. Query classification (data vs narrative)
2. Retrieval pipeline (FTS + vector search)
3. Graph expansion (refers_to, supports edges, depth 1 only)
4. Context pack assembly with token budgets:
   - Global budget: CONTEXT_BUDGET_TOKENS (default 10,000)
   - Quotas: conversation 500, claims/briefs 1,500, narrative 4,000, data 4,000
   - Supplements ≤25% of narrative quota unless user asks
   - Explicitly referenced objects (Table/Box/Chart) are "must-include"
   - Include last 3 user + 3 assistant turns (truncated to memory quota)
5. LLM prompt with strict JSON schema
6. Response validation and retry logic
7. SSE streaming endpoint
8. Evidence endpoints

**Deliverables:**
- `POST /api/chat` creates conversation
- `GET /api/chat/stream/{conversation_id}` (SSE)
- Response JSON: `{answer, intuition, evidence, followups}`
- Context pack validates token budget and quota compliance
- **Stop condition:** No uncited numeric claims
- **Stop condition:** Context pack exceeds CONTEXT_BUDGET_TOKENS → STOP
- **Stop condition:** Explicitly referenced evidence (e.g., "Table I.2a") missing from pack → STOP
- **Stop condition:** Supplement quota violated (>25% unless requested) → STOP

---

### **Phase 8: Analytics Logging & Insights**
**Goal:** Measure usage and sentiment with structured rollups

**Tasks:**
1. Runtime logging (conversations, messages, retrieval_events with full citation data)
2. Offline labeling job:
   - Classify messages into topics, entities, intent, sentiment (optimistic/neutral/pessimistic/mixed), concerns
   - Store in message_labels with confidence scores
3. Offline clustering job (weekly):
   - Embed user questions
   - Cluster into themes
   - Store in topic_clusters with summaries
4. Offline rollup job (daily):
   - Compute daily_insights: total questions, top_topics, top_concerns, sentiment mix, notable questions, coverage gaps
5. Admin analytics endpoints

**Deliverables:**
- Chat logs all interactions with retrieval_events including used_evidence
- Scripts: `label_messages.py`, `cluster_topics.py` (offline jobs)
- daily_insights table populated with: total_questions, top_topics, top_concerns, sentiment_mix, notable_questions, coverage_gaps
- Admin endpoints: GET /api/admin/insights?start=...&end=..., GET /api/admin/top_questions?start=...&end=...
- "Coverage gaps" = questions with low evidence coverage (for improvement backlog)

---

### **Phase 9: Frontend (Summary & Chat Pages)**
**Goal:** Two user-facing pages with evidence panels and Netlify-compatible routing

**Tasks:**
1. Summary Page (`/summary.html?corpus_id=...` or with Netlify redirects)
2. Chat Page (`/chat.html?corpus_id=...` or with Netlify redirects)
3. Login Page with privacy disclosure
4. Shared components (Evidence drawer/panel)
5. Netlify configuration:
   - Option A: Use query params (simplest): summary.html?corpus_id=X, chat.html?corpus_id=X
   - Option B: Add netlify.toml redirects rewriting /summary/* → /summary.html, /chat/* → /chat.html
6. CORS + cookie configuration:
   - If backend on different domain (Cloud Run), set cookies: SameSite=None; Secure
   - Configure CORS origin to frontend domain
   - Consider serving frontend from backend static folder OR same apex domain for simpler sessions

**Deliverables:**
- Static HTML/CSS/JS files (or served from backend)
- GitHub repo configured for Netlify auto-deploy
- netlify.toml with redirects (if using path routing) OR use query params
- Environment variables for API endpoint
- CORS/cookie settings documented for deployment

---

### **Phase 10: Deployment & Testing**
**Goal:** Production-ready system on GCP + Netlify

**Tasks:**
1. Backend deployment (GCP Cloud SQL + Cloud Run)
2. Frontend deployment (Netlify from GitHub)
3. CI/CD setup
4. Acceptance testing

**Deliverables:**
- Live application accessible via URL
- All acceptance tests passing
- Documentation for ingestion and deployment

---

## 🔑 Required Before Starting

### **1. Source Data Files**
- [ ] Economic Survey PDF(s)
- [ ] Economic Survey XLSX datasets
- [ ] Supplementary reports (optional)
- [ ] Sample test files (tabchart1.xlsx, tab1.1.xlsx)

### **2. GCP Credentials & Setup**
- [ ] GCP project ID
- [ ] Service account JSON key
- [ ] Cloud SQL instance details
- [ ] Preferred region

### **3. Google OAuth Credentials**
- [ ] `GOOGLE_CLIENT_ID`
- [ ] `GOOGLE_CLIENT_SECRET`
- [ ] Authorized redirect URIs

### **4. LLM API Credentials**
- [ ] OpenAI API key OR Anthropic API key
- [ ] Preferred model
- [ ] Embedding model preference

### **5. GitHub Repository**
- [ ] GitHub account and repo name
- [ ] Write access for pushing code

### **6. Configuration Values**
- [ ] `SERVER_SALT` (random string)
- [ ] `SESSION_SECRET` (random string)
- [ ] Preferred corpus name

---

## 📊 Estimated Timeline

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| Phase 1 | 1 day | None |
| Phase 2 | 1 day | Phase 1 + Google OAuth creds |
| Phase 3 | 2 days | Phase 1 + XLSX files |
| Phase 4 | 1 day | Phase 3 |
| Phase 5 | 2-3 days | Phase 1 + PDF files |
| Phase 6 | 1-2 days | Phases 3,4,5 + LLM API |
| Phase 7 | 2-3 days | Phases 5,6 + LLM API |
| Phase 8 | 1 day | Phase 7 |
| Phase 9 | 2-3 days | Phase 7 |
| Phase 10 | 1-2 days | All phases + GCP setup |
/tokens → STOP
2. **Phase 3:** XLSX doesn't split Table I.1 panels → STOP
3. **Phase 5:** "Chart I.x" doesn't link PDF ↔ XLSX → STOP
4. **Phase 5:** Edge rel_types include values other than {contains, refers_to, supports} → STOP
5. **Phase 5:** Embeddings generated at runtime (not offline) → STOP
6. **Phase 6:** Claim card has zero evidence → STOP
7. **Phase 7:** Chat emits uncited numeric claim → STOP
8. **Phase 7:** Context pack exceeds CONTEXT_BUDGET_TOKENS → STOP
9. **Phase 7:** Explicitly referenced evidence (Table/Box/Chart) missing from pack → STOP
10. **Phase 9:** Frontend deployed without proper Netlify routing/redirects → STOP
11. **Any Phase:** Runtime parsing of XLSX/PDF detected → STOP
12. **Any Phase:** Ingestion modules imported in backend runtime code → STOP (use static code scan in CI)

---

## 📁 Project Structure

```
survey-practitioner-chat/
├── backend/
│   ├── app/
│   │   ├── models/         # SQLAlchemy models
│   │   ├── api/            # FastAPI routers
│   │   ├── core/           # Config, database, auth
│   │   ├── services/       # Business logic
│   │   └── main.py         # FastAPI app
│   ├── migrations/
│   │   └── init.sql        # Database schema
│   ├── requirements.txt
│   └── Dockerfile
├── ingestion/
│   ├── pdf_ingest.py       # PDF processing
│   ├── xlsx_ingest.py      # XLSX processing
│   ├── indicators.py       # Indicator registry
│   ├── summaries.py        # Topic briefs & claims
│   ├── label_messages.py   # Analytics labeling
│   ├── cluster_topics.py   # Analytics clustering
│   └── requirements.txt
├── frontend/
│   ├── index.html          # Landing page
│   ├── summary.html        # Summary page
│   ├── chat.html           # Chat page
│   ├── css/
│   │   └── styles.css
│   ├── js/
│   │   ├── auth.js
│   │   ├── summary.js
│   │   ├── chat.js
│   │   └── evidence.js
│   └── netlify.toml
├── docker-compose.yml
├── README.md
└── .env.example
```
