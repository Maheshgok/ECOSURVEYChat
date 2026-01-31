# Phase 1 Local Development Setup (Windows)

**Objective:** Test Phase 1 foundation (database, models, health check) with local PostgreSQL  
**Environment:** Windows 10/11  
**Estimated Time:** 30-45 minutes

---

## Step 1: Install PostgreSQL 15 (10 minutes)

### Option A: Using Windows Installer (Recommended)

1. **Download PostgreSQL 15**
   - Go to: https://www.postgresql.org/download/windows/
   - Click "Download the installer"
   - Select Version 15.x (latest)

2. **Run Installer**
   - Accept default installation directory
   - **Important:** Remember the password you set for `postgres` user (use `postgres` for easy testing)
   - Port: 5432 (default)
   - Locale: Default (English, United States)

3. **Verify Installation**
   ```powershell
   # Open PowerShell and test connection
   psql -U postgres -c "SELECT version();"
   # Should display PostgreSQL version
   ```

### Option B: Using Chocolatey

```powershell
choco install postgresql15 --params '/Password:postgres'
```

### Option C: Using Windows Subsystem for Linux (WSL)

```bash
# In WSL terminal
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo service postgresql start
```

---

## Step 2: Install pgvector Extension (5-10 minutes)

### For Windows Native Installation

1. **Download pgvector for Windows**
   - Go to: https://github.com/pgvector/pgvector/releases
   - Download: `pgvector-{version}-pg15-win64.zip`

2. **Install pgvector**
   ```powershell
   # Extract zip to PostgreSQL lib directory
   # (Usually: C:\Program Files\PostgreSQL\15\lib)
   
   # Then run in PowerShell as Admin:
   cd 'C:\Program Files\PostgreSQL\15\lib'
   # Extract vector.dll from the zip
   ```

3. **Verify in PostgreSQL**
   ```powershell
   psql -U postgres -c "CREATE EXTENSION IF NOT EXISTS vector;"
   # Should return: CREATE EXTENSION
   ```

### For WSL Installation

```bash
# In WSL
sudo apt install postgresql-15-pgvector
# Or build from source:
git clone https://github.com/pgvector/pgvector.git
cd pgvector
make
sudo make install
```

---

## Step 3: Create Database and Schema (5 minutes)

1. **Create the database**
   ```powershell
   psql -U postgres -c "CREATE DATABASE survey_chat;"
   ```

2. **Connect and create pgvector extension**
   ```powershell
   psql -U postgres -d survey_chat -c "CREATE EXTENSION IF NOT EXISTS vector;"
   ```

3. **Run migrations** (one of two options):

   **Option A: Using SQL file**
   ```powershell
   psql -U postgres -d survey_chat -f "backend\migrations\001_init.sql"
   ```

   **Option B: Using Python** (Step 4)

---

## Step 4: Set Up Python Environment (10 minutes)

1. **Navigate to backend directory**
   ```powershell
   cd 'c:\Users\Dell 5330\OneDrive\Documents\ECOSURVEYCHat\backend'
   ```

2. **Create virtual environment**
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

3. **Install dependencies**
   ```powershell
   pip install -r requirements.txt
   ```

4. **Test imports**
   ```powershell
   python -c "from app.models import *; print('✓ All models imported')"
   ```

---

## Step 5: Initialize Database (Optional - if not using SQL file)

1. **Create Python script** (`backend\init_db.py`):
   ```python
   from app.core.database import init_db, migrate_db
   
   if __name__ == "__main__":
       print("Creating tables...")
       init_db()
       print("✓ Tables created")
       
       print("Running migrations...")
       migrate_db()
       print("✓ Migrations complete")
   ```

2. **Run initialization**
   ```powershell
   cd backend
   python init_db.py
   ```

---

## Step 6: Test API Health Check (5 minutes)

1. **Start FastAPI server**
   ```powershell
   cd backend
   python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

2. **Test health endpoint** (in another PowerShell window)
   ```powershell
   Invoke-WebRequest -Uri "http://localhost:8000/health" -Method GET
   # Should return: {"status": "ok", "database": "connected", ...}
   ```

3. **View Swagger UI**
   - Open browser: http://localhost:8000/docs
   - Should see all 6 routers (health, auth, briefing, chat, evidence, admin)

---

## Step 7: Verify Database Tables (5 minutes)

1. **Connect to database**
   ```powershell
   psql -U postgres -d survey_chat
   ```

2. **List all tables**
   ```sql
   \dt
   ```

3. **Expected output** (19 tables):
   ```
   corpora
   documents
   nodes
   edges
   data_files
   data_sheets
   data_tables
   indicators
   indicator_series
   topic_briefs
   claim_cards
   search_index
   embeddings
   sessions
   conversations
   messages
   retrieval_events
   message_labels
   topic_clusters
   daily_insights
   ingestion_runs
   ```

4. **Check pgvector**
   ```sql
   SELECT extname FROM pg_extension WHERE extname = 'vector';
   -- Should return: vector
   ```

5. **Exit psql**
   ```sql
   \q
   ```

---

## Step 8: Test Python Models (5 minutes)

1. **Create test script** (`backend\test_models.py`):
   ```python
   from app.core.database import SessionLocal
   from app.models import Corpus, Document, Node, Edge
   
   # Test connection
   session = SessionLocal()
   
   try:
       # Test model imports
       print("✓ All models imported successfully")
       
       # Test database connection
       result = session.execute("SELECT COUNT(*) FROM corpora")
       count = result.scalar()
       print(f"✓ Database connected: {count} corpora")
       
       # Test model creation (without saving)
       corpus = Corpus(
           name="Test Economic Survey",
           description="Phase 1 test"
       )
       print(f"✓ Model instantiated: {corpus.name}")
       
   except Exception as e:
       print(f"✗ Error: {e}")
   finally:
       session.close()
   ```

2. **Run test**
   ```powershell
   cd backend
   python test_models.py
   ```

3. **Expected output**:
   ```
   ✓ All models imported successfully
   ✓ Database connected: 0 corpora
   ✓ Model instantiated: Test Economic Survey
   ```

---

## Troubleshooting

### PostgreSQL Connection Error
```
Error: could not translate host name "localhost" to address
```
**Solution:**
- Verify PostgreSQL is running: `services.msc` → PostgreSQL service should be "Running"
- Check port 5432 is open: `netstat -an | findstr 5432`
- Use `127.0.0.1` instead of `localhost` in DATABASE_URL

### pgvector Not Found
```
ERROR: extension "vector" does not exist
```
**Solution:**
- Verify installation: `psql -U postgres -c "\dx vector"`
- May need to build from source (see WSL option above)
- Or temporarily skip pgvector (use `-- CREATE EXTENSION` comment in migration)

### Python Models Import Error
```
ModuleNotFoundError: No module named 'sqlalchemy'
```
**Solution:**
- Verify venv is activated: Should see `(venv)` in PowerShell prompt
- Reinstall: `pip install -r requirements.txt`

### Port 8000 Already in Use
```
Address already in use
```
**Solution:**
```powershell
# Find process using port 8000
Get-NetTCPConnection -LocalPort 8000 | Select-Object OwningProcess
# Kill it
Stop-Process -Id <PID> -Force
```

---

## Phase 1 Acceptance Checklist

Run this checklist to verify Phase 1 completion:

- [ ] PostgreSQL 15 installed and running
- [ ] pgvector extension installed and active
- [ ] Database `survey_chat` created
- [ ] 19 tables created from migration
- [ ] Python venv created and activated
- [ ] All dependencies installed
- [ ] FastAPI server starts without errors
- [ ] Health endpoint returns 200 OK
- [ ] Swagger UI loads at `/docs`
- [ ] All 19 models import without errors
- [ ] Database connection test passes
- [ ] At least 1 table query works

**If all boxes checked:** ✅ Phase 1 Foundation Complete

---

## Quick Commands Reference

```powershell
# PostgreSQL
psql -U postgres -d survey_chat              # Connect to DB
\dt                                          # List tables
\dx                                          # List extensions
\q                                           # Exit

# Python (from backend directory)
.\venv\Scripts\Activate.ps1                  # Activate venv
pip install -r requirements.txt              # Install deps
python -m uvicorn app.main:app --reload      # Start API
python test_models.py                        # Test models

# API Testing (from any directory)
Invoke-WebRequest http://localhost:8000/health   # Health check
Start-Process "http://localhost:8000/docs"       # Open Swagger UI
```

---

## Next Steps (Phase 2)

Once Phase 1 passes:
1. Implement Google OAuth in `backend/app/api/auth.py`
2. Add session tracking
3. Test login/logout flow
4. Then move to Phase 3 (data ingestion)

---

**Estimated Total Time:** 30-45 minutes  
**Key Goal:** Verify foundation works locally before adding Docker complexity  
**Success Indicator:** Health endpoint returns status=ok with database connected

