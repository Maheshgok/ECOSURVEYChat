# Database Skills (Phase 1)

**Goal:** Working PostgreSQL database with all tables and API skeleton

---

## 📋 Prerequisites

- Docker and Docker Compose installed
- Python 3.11+ installed
- Basic SQL knowledge
- Understanding of SQLAlchemy ORM

---

## 🎯 Tasks Breakdown

### **Task 1.1: Create Project Structure**

```
survey-practitioner-chat/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── config.py
│   │   │   └── database.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── corpus.py
│   │   │   ├── document.py
│   │   │   ├── node.py
│   │   │   ├── edge.py
│   │   │   ├── data.py
│   │   │   ├── indicator.py
│   │   │   ├── summary.py
│   │   │   ├── search.py
│   │   │   └── analytics.py
│   │   └── api/
│   │       ├── __init__.py
│   │       └── health.py
│   ├── migrations/
│   │   └── 001_init.sql
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── docker-compose.yml
└── README.md
```

**Actions:**
1. Create all directories and `__init__.py` files
2. Create empty Python files for models
3. Create `requirements.txt` with initial dependencies

---

### **Task 1.2: Write Database Schema (`migrations/001_init.sql`)**

Create SQL migration file with all required tables (19 total in Spec v1.2):

**Tables to create:**
1. `corpora` - Corpus metadata
2. `documents` - PDF reports
3. `nodes` - Evidence units
4. `edges` - Relationships between nodes
5. `data_files` - XLSX files
6. `data_sheets` - XLSX sheets
7. `data_tables` - Extracted tables
8. `indicators` - Indicator registry
9. `indicator_series` - Time series data
10. `topic_briefs` - Summary briefings
11. `claim_cards` - Evidence-backed claims
12. `search_index` - Full-text search
13. `embeddings` - Vector embeddings
14. `conversations` - Chat sessions
15. `messages` - Chat messages
16. `retrieval_events` - Evidence usage logs
17. `message_labels` - Analytics labels
18. `daily_insights` - Rollup analytics
19. `topic_clusters` - Clustered themes

**Required extensions:**
```sql
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgvector";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
```

**Key considerations:**
- Use JSONB for flexible metadata fields
- Create indexes on foreign keys
- Create GIN indexes for JSONB and full-text search
- Use `vector(1536)` for embeddings (OpenAI default)
- Add timestamps (created_at, updated_at) where needed

---

### **Task 1.3: Create SQLAlchemy Models**

For each table, create a corresponding SQLAlchemy model.

**Example: `models/corpus.py`**
```python
from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.sql import func
from app.core.database import Base

class Corpus(Base):
    __tablename__ = "corpora"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

**Guidelines:**
- Inherit from `Base` (declarative base)
- Use proper type mappings (JSONB → JSON in SQLAlchemy)
- Define relationships for foreign keys
- No extra fields beyond spec
- Include `__repr__` for debugging

---

### **Task 1.4: Database Connection Utilities**

**File: `core/config.py`**
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    SERVER_SALT: str
    SESSION_SECRET: str
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    LLM_API_KEY: str
    EMBEDDING_MODEL_ID: str = "text-embedding-3-large"
    
    class Config:
        env_file = ".env"

settings = Settings()
```

**File: `core/database.py`**
```python
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

---

### **Task 1.5: FastAPI App Skeleton**

**File: `main.py`**
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Economic Survey Practitioner Chat")

# CORS for Netlify frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "Economic Survey Practitioner Chat API"}

# Health check
from app.api import health
app.include_router(health.router, prefix="/api", tags=["health"])
```

**File: `api/health.py`**
```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db

router = APIRouter()

@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    try:
        # Test database connection
        db.execute("SELECT 1")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
```

---

### **Task 1.6: Docker Configuration**

**File: `docker-compose.yml`**
```yaml
version: '3.8'

services:
  postgres:
    image: pgvector/pgvector:pg15
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: survey_chat
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backend/migrations:/docker-entrypoint-initdb.d

  api:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://postgres:postgres@postgres:5432/survey_chat
    depends_on:
      - postgres
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

volumes:
  postgres_data:
```

**File: `backend/Dockerfile`**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**File: `backend/requirements.txt`**
```
fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy==2.0.23
psycopg2-binary==2.9.9
pydantic==2.5.0
pydantic-settings==2.1.0
python-multipart==0.0.6
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
httpx==0.25.2
pgvector==0.2.4
```

---

### **Task 1.7: Environment Variables**

**File: `backend/.env.example`**
```
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/survey_chat
SERVER_SALT=<random-string>
SESSION_SECRET=<random-string>
GOOGLE_CLIENT_ID=<your-google-client-id>
GOOGLE_CLIENT_SECRET=<your-google-client-secret>
LLM_API_KEY=<your-llm-api-key>
EMBEDDING_MODEL_ID=text-embedding-3-large
```

---

## ✅ Acceptance Criteria

### **Test 1: Database Connection**
```bash
docker-compose up -d postgres
# Wait 10 seconds for postgres to start
docker-compose exec postgres psql -U postgres -d survey_chat -c "\dt"
```
**Expected:** List of 19 tables

### **Test 2: API Health Check**
```bash
docker-compose up -d
curl http://localhost:8000/api/health
```
**Expected:** `{"status": "healthy", "database": "connected"}`

### **Test 3: Model Imports**
```python
from app.models import corpus, document, node, edge
# Should not raise ImportError
```

---

## 🎯 Deliverables Checklist

- [ ] All directories created
- [ ] `migrations/001_init.sql` with all 19 tables
- [ ] SQLAlchemy models for all tables
- [ ] Database connection utilities (`config.py`, `database.py`)
- [ ] FastAPI app with health endpoint
- [ ] `docker-compose.yml` working
- [ ] `Dockerfile` for backend
- [ ] `requirements.txt` with dependencies
- [ ] `.env.example` with all variables
- [ ] `docker-compose up` starts successfully
- [ ] Health endpoint returns 200
- [ ] All tables exist in database

### 🔒 **CRITICAL RULE: Schema Consistency**

**Models must EXACTLY match migrations.sql.**

- If you need to change schema, update `migrations/001_init.sql` FIRST
- Never "fix it in SQLAlchemy" and expect it to work in production
- Any schema drift between migrations and models will cause deployment failures
- When in doubt, regenerate the database from migrations and verify models match
- Use `psql` to inspect actual schema vs what models expect

---

## 🔗 Next Phase

Once all deliverables are complete and tests pass, proceed to:
- **Phase 2: Auth Skills** (if OAuth credentials ready)
- **Phase 3: XLSX Ingestion Skills** (if data files ready)
- **Phase 5: PDF Ingestion Skills** (if PDF files ready)
