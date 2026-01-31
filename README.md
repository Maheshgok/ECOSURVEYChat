# Economic Survey Practitioner Chat v1.2

A specialized RAG (Retrieval-Augmented Generation) system for navigating economic survey data with structured evidence linking, built on PostgreSQL, FastAPI, and vanilla JavaScript.

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.11+ (for local development)
- PostgreSQL 15+ (included in Docker)
- Google OAuth credentials (for authentication)

### Setup (5 minutes)

1. **Clone and configure:**
```bash
cp .env.example .env
# Edit .env with your Google OAuth credentials and database settings
```

2. **Start services:**
```bash
docker-compose up
```

3. **Access the application:**
- Frontend: http://localhost:3000
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## Architecture

### Stack
- **Backend:** FastAPI + SQLAlchemy + PostgreSQL 15 + pgvector
- **Frontend:** HTML5 + CSS3 + Vanilla JavaScript (no build tools required)
- **Infrastructure:** Docker Compose + Dockerfile
- **Database:** 19 tables across 4 categories (core, datasets, summaries, analytics)

### Database Schema

#### Core Tables
- `corpora` - Document collections (e.g., "Economic Survey 2024")
- `documents` - Individual documents with metadata
- `nodes` - Evidence nodes (text excerpts with location references)
- `edges` - Evidence relationships (contains, refers_to, supports)

#### Dataset Tables
- `data_files` - Uploaded XLSX/CSV files
- `data_sheets` - Sheets within files
- `data_tables` - Panel tables from sheets
- `indicators` - Derived metrics (year/region aggregates)
- `indicator_series` - Time series of indicators

#### Summary Tables
- `topic_briefs` - Executive summaries with supporting evidence
- `claim_cards` - Factual claims with evidence links
- `search_index` - Full-text search index
- `embeddings` - OpenAI embeddings for semantic search

#### Analytics Tables
- `sessions` - User sessions (pseudonymous)
- `conversations` - Multi-turn conversations
- `messages` - Individual messages
- `retrieval_events` - Evidence retrieval tracking
- `message_labels` - Human labels for model outputs
- `topic_clusters` - Offline topic aggregation
- `daily_insights` - Daily aggregated analytics

### Key Features

1. **Structured Evidence**: Every claim links to specific text excerpts with precise locations
2. **Offline Ingestion**: One-time bulk processing of documents and datasets
3. **Token Budget**: Global (10K) + per-conversation (500) quotas enforced
4. **Pseudonymous Tracking**: SHA256(google_sub + SERVER_SALT) for privacy
5. **Semantic Search**: pgvector integration for embeddings-based retrieval
6. **Data Panel Splitting**: XLSX tables automatically split by country/region dimensions

## Configuration

### Environment Variables (.env)

**Database:**
```
DATABASE_HOST=postgres
DATABASE_PORT=5432
DATABASE_NAME=ecosurvey
DATABASE_USER=postgres
DATABASE_PASSWORD=your_secure_password
```

**Google OAuth:**
```
GOOGLE_CLIENT_ID=your_client_id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your_secret
GOOGLE_REDIRECT_URI=http://localhost:3000/callback
```

**Security:**
```
SESSION_SECRET=your_random_256bit_hex_string
SERVER_SALT=your_random_salt_for_pseudonymization
```

**LLM Provider:**
```
LLM_PROVIDER=openai  # or anthropic
OPENAI_API_KEY=sk-...
# or
ANTHROPIC_API_KEY=sk-ant-...
```

**Context Budgets:**
```
CONTEXT_BUDGET_GLOBAL=10000
CONTEXT_BUDGET_CONVERSATION=500
CONTEXT_BUDGET_CLAIMS=1500
CONTEXT_BUDGET_NARRATIVE=4000
CONTEXT_BUDGET_DATA=4000
CONTEXT_SUPPLEMENT_PCT=20
```

**Ingestion:**
```
INGESTION_MODE=skip  # skip or strict (for file pattern enforcement)
```

## API Endpoints

### Health
- `GET /health` - Service health check

### Authentication (Phase 2)
- `POST /login` - Initiate OAuth flow
- `GET /callback` - OAuth callback handler
- `POST /logout` - Session termination

### Briefing (Phase 6)
- `GET /corpus/{corpus_id}/briefing` - 3-5 minute briefing with topline, topics, key numbers

### Chat (Phase 7)
- `POST /api/chat` - Send message, get response + evidence
- `GET /api/chat/stream/{conversation_id}` - Server-sent events streaming

### Evidence (Phase 7)
- `GET /evidence/node/{id}` - Retrieve text excerpt with context
- `GET /evidence/table/{id}` - Retrieve data table
- `GET /evidence/series/{id}` - Retrieve time series data

### Admin (Phase 8)
- `GET /insights` - Daily aggregated insights
- `GET /top_questions` - Popular user questions

## Frontend Pages

### index.html
Landing page with navigation, feature overview, CTA buttons to Summary and Chat.

### summary.html
3-5 minute briefing with:
- Topline bullets (top 5 key findings)
- Topic briefs (expandable cards)
- Key numbers (important metrics)
- Evidence drawer (citations)

### chat.html
ChatGPT-like multi-turn chat with:
- Message transcript (user/assistant)
- Real-time streaming (optional)
- Show intuition toggle (LLM reasoning)
- Evidence panel (right sidebar)

## Development Workflow

### Phase 1: Foundation
- Database schema validation
- Health check endpoint
- ORM model verification
- Docker Compose testing

### Phase 2: Authentication
- Google OAuth flow
- Session management
- User identification
- Logout handling

### Phase 3-4: Data Ingestion
- XLSX parsing with panel splitting
- PDF extraction (PyMuPDF)
- Evidence node creation
- Indicator aggregation

### Phase 5: Summarization
- Topic brief generation
- Claim extraction
- Evidence linking
- Summary storage

### Phase 6: Briefing API
- Corpus briefing endpoint
- Top-K retrieval
- Summary formatting
- Response caching

### Phase 7: Chat & Retrieval
- Conversation management
- Message context assembly
- Token budget enforcement
- Server-sent events streaming
- Evidence citation

### Phase 8: Analytics
- Message labeling endpoints
- Topic clustering
- Daily insights aggregation
- Search quality metrics

### Phase 9: Frontend Interactivity
- Navigation and routing
- API integration
- Real-time updates
- Evidence panel interaction

### Phase 10: Deployment
- GCP setup (Cloud Run, Cloud SQL)
- Netlify frontend deployment
- GitHub Actions CI/CD
- Environment promotion

## Local Development

### Setup Python Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
cd backend
pip install -r requirements.txt
cd ../ingestion
pip install -r requirements.txt
```

### Run Backend Only
```bash
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Run Frontend Dev Server
```bash
cd frontend
python -m http.server 3000
```

### Database Migrations
```bash
# Migrations run automatically in Docker on startup
# For local PostgreSQL:
psql -h localhost -U postgres -d ecosurvey -f backend/migrations/001_init.sql
```

## Testing

### API Tests (Phase 1)
```bash
cd backend
pytest tests/test_health.py -v
pytest tests/test_models.py -v
```

### Database Tests
```bash
cd backend
python -c "from app.core.database import init_db; init_db()"
```

### Integration Tests (Post-Phase 6)
```bash
docker-compose up -d
sleep 5
curl http://localhost:8000/health
curl http://localhost:8000/docs
```

## Performance Considerations

1. **pgvector Indexing**: HNSW indexes on embeddings (1536-dim)
2. **FTS Optimization**: GIN indexes on search_index.tsv
3. **Connection Pooling**: SQLAlchemy NullPool for serverless (GCP)
4. **Query Optimization**: Foreign key indexes, strategic JSONB fields
5. **Caching**: Frontend service worker ready (Phase 9+)

## Troubleshooting

### Database Connection Issues
```bash
# Check postgres container logs
docker-compose logs postgres

# Verify connection
docker exec ecosurvey-postgres-1 psql -U postgres -c "SELECT version();"
```

### API Health Check
```bash
curl http://localhost:8000/health
```

### Frontend Issues
- Check browser console (F12)
- Verify API_URL in frontend/js/app.js
- Check CORS headers in Backend logs

### Missing Environment Variables
```bash
# Copy template and fill in values
cp .env.example .env
nano .env
```

## File Structure
```
.
├── backend/
│   ├── app/
│   │   ├── core/          # Config, database, settings
│   │   ├── models/        # SQLAlchemy ORM models
│   │   ├── api/           # Route handlers
│   │   ├── services/      # Business logic (Phase 3+)
│   │   └── main.py        # FastAPI app
│   ├── migrations/        # SQL schema files
│   ├── tests/            # Unit & integration tests
│   ├── requirements.txt
│   └── Dockerfile
├── ingestion/
│   ├── xlsx_ingest.py    # Excel parsing (Phase 3)
│   ├── pdf_ingest.py     # PDF extraction (Phase 4)
│   ├── indicators.py     # Metric aggregation (Phase 5)
│   ├── summaries.py      # Brief generation (Phase 5)
│   └── requirements.txt
├── frontend/
│   ├── css/styles.css    # Responsive styling
│   ├── js/
│   │   ├── app.js        # Navigation & utilities
│   │   ├── chat.js       # Chat logic
│   │   └── summary.js    # Summary page logic
│   ├── index.html        # Landing page
│   ├── summary.html      # Briefing page
│   └── chat.html         # Chat page
├── docker-compose.yml
├── .env.example
└── README.md
```

## Contributing

1. Follow the phase-based development roadmap
2. Run tests before committing
3. Update documentation for API changes
4. Use type hints in Python code
5. Test responsive design (mobile, tablet, desktop)

## License

Proprietary - Economic Survey Practitioner Chat v1.2

## Support

For issues or questions, refer to:
- Implementation_Plan.md - Development roadmap
- Spec_Doc.md - Technical specification
- Skills guides - Phase-specific implementations
- Common_Errors guide - Troubleshooting
