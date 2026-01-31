# Phase 1 Quick Start - Local Development (Windows)

**Status:** Ready to Execute  
**Duration:** 30-45 minutes  
**Objective:** Verify database, models, and API health check locally

---

## Prerequisites Check

Before starting, verify you have:
- [ ] Python 3.10+ installed (`python --version`)
- [ ] PostgreSQL 15 OR willing to install
- [ ] 2 PowerShell windows available
- [ ] Internet connection for downloads

---

## Quick Start (3 Simple Steps)

### Step 1: Install PostgreSQL (if needed)

```powershell
# Windows: Download from https://www.postgresql.org/download/windows/
# Or use Chocolatey:
choco install postgresql15 --params '/Password:postgres'

# After installation, verify:
psql -U postgres -c "SELECT version();"
# Should display PostgreSQL version
```

**Estimated time:** 10-15 minutes

---

### Step 2: Create Database & Activate Environment

Open **PowerShell Window #1**:

```powershell
# Create database
psql -U postgres -c "CREATE DATABASE survey_chat;"

# Navigate to project
cd 'c:\Users\Dell 5330\OneDrive\Documents\ECOSURVEYCHat'

# Activate Python environment
.\.venv\Scripts\Activate.ps1

# Verify activation (should see (.venv) in prompt)
python --version
```

**Estimated time:** 2-3 minutes

---

### Step 3: Initialize Database & Start API

Still in **PowerShell Window #1**:

```powershell
# Move to backend directory
cd backend

# Initialize database (creates all tables)
python init_phase1.py
# Should see: ✓ Phase 1 Initialization Complete!

# Start FastAPI server
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
# Should see: Uvicorn running on http://127.0.0.1:8000
```

**Estimated time:** 3-5 minutes

---

## Verification (Parallel Testing)

Open **PowerShell Window #2** (environment still activated from Step 2):

```powershell
# Test 1: Health Check
Invoke-WebRequest -Uri "http://localhost:8000/health" -Method GET
# Should return: {"status":"ok","database":"connected",...}
echo "✓ Health check passed"

# Test 2: Models Import
python -c "from app.models import *; print('✓ All 19 models imported')"

# Test 3: Database Query
python << 'EOF'
from app.core.database import SessionLocal
from app.models import Corpus

session = SessionLocal()
count = session.query(Corpus).count()
print(f"✓ Database query works: {count} corpora")
session.close()
EOF

# Test 4: Swagger UI
Start-Process "http://localhost:8000/docs"
# Browser should open with API documentation
```

**Estimated time:** 2 minutes

---

## Expected Output

### Health Endpoint Response
```json
{
  "status": "ok",
  "database": "connected",
  "timestamp": "2026-01-31T00:30:00Z",
  "models_ready": 19,
  "version": "1.2"
}
```

### Swagger UI
- URL: http://localhost:8000/docs
- Should show 6 routers:
  - ✓ health (GET /health)
  - ✓ auth (POST /login, /callback, /logout)
  - ✓ briefing (GET /corpus/{corpus_id}/briefing)
  - ✓ chat (POST /api/chat)
  - ✓ evidence (GET /evidence/*)
  - ✓ admin (GET /insights, /top_questions)

### Database Tables
```powershell
psql -U postgres -d survey_chat -c "\dt"
# Should list 21 tables:
# corpora, documents, nodes, edges, data_files, data_sheets,
# data_tables, indicators, indicator_series, topic_briefs,
# claim_cards, search_index, embeddings, sessions, conversations,
# messages, retrieval_events, message_labels, topic_clusters,
# daily_insights, ingestion_runs
```

---

## Phase 1 Acceptance Criteria

✅ **All of the following must be true:**

- [ ] PostgreSQL running locally on port 5432
- [ ] Database `survey_chat` exists
- [ ] 21 tables created successfully
- [ ] Python venv activated and working
- [ ] All dependencies installed
- [ ] `init_phase1.py` runs successfully
- [ ] FastAPI server starts on port 8000
- [ ] Health endpoint returns 200 OK
- [ ] Swagger UI loads at `/docs`
- [ ] All 19 models import without errors
- [ ] Database queries work from Python

**Result:** If all boxes checked, Phase 1 is COMPLETE ✅

---

## Troubleshooting

### Error: "could not connect to server: No such file or directory"
```
Problem: PostgreSQL not running
Solution:
  - Windows: services.msc → Start "postgresql-x64-15" service
  - Or restart PostgreSQL: net start postgresql-x64-15
```

### Error: "database 'survey_chat' does not exist"
```
Problem: Database not created
Solution:
  psql -U postgres -c "CREATE DATABASE survey_chat;"
```

### Error: "ModuleNotFoundError: No module named 'fastapi'"
```
Problem: Dependencies not installed
Solution:
  - Verify venv is activated (should see (.venv) in prompt)
  - Reinstall: pip install -r requirements.txt
```

### Error: "Address already in use (:8000)"
```
Problem: Port 8000 is in use
Solution:
  Get-NetTCPConnection -LocalPort 8000 | Select-Object OwningProcess
  Stop-Process -Id <PID> -Force
```

---

## What's Next After Phase 1?

Once Phase 1 is complete:

1. **Phase 2 (OAuth):** Implement Google OAuth authentication
2. **Phase 3-5 (Ingestion):** Build XLSX/PDF data pipeline
3. **Phase 6 (Briefing):** Create executive summary API
4. **Phase 7 (Chat):** Implement LLM chat with retrieval
5. **Phase 8 (Analytics):** Add tracking and insights
6. **Phase 9 (Frontend):** Build interactive UI
7. **Phase 10 (Deployment):** Deploy to GCP + Netlify

---

## Quick Command Reference

```powershell
# PostgreSQL
psql -U postgres -d survey_chat           # Connect to DB
CREATE DATABASE survey_chat;               # Create DB
\dt                                        # List tables
\q                                         # Exit psql

# Python (from project root)
.\.venv\Scripts\Activate.ps1               # Activate venv
deactivate                                 # Deactivate venv
pip install -r backend\requirements.txt    # Install deps

# Backend (from backend directory)
python init_phase1.py                      # Initialize DB
python -m uvicorn app.main:app --reload    # Start API
python -c "from app.models import *"       # Test imports

# API Testing
curl http://localhost:8000/health          # Health check (if curl available)
Invoke-WebRequest http://localhost:8000/health  # PowerShell version
Start-Process "http://localhost:8000/docs" # Open Swagger UI
```

---

## Support Resources

- **Setup Guide:** See [PHASE_1_LOCAL_SETUP.md](PHASE_1_LOCAL_SETUP.md)
- **Testing Guide:** See [PHASE_1_TESTING.md](PHASE_1_TESTING.md)
- **Architecture:** See [Spec_Doc.md](Spec_Doc.md)
- **Skills Guide:** See [Skills/01_Phase1_Foundation_Skills.md](Skills/01_Phase1_Foundation_Skills.md)

---

**Status:** Ready to begin Phase 1 ✅  
**Estimated Duration:** 30-45 minutes  
**Success Metric:** Health endpoint returns `{"status":"ok","database":"connected"}`

