# Phase 1 Testing Guide

## Objective
Verify foundation: database schema, models, Docker infrastructure, and health endpoints.

## Prerequisites
- Docker & Docker Compose installed
- `.env` file configured (copy from `.env.example`)
- Terminal access to workspace directory

## Quick Validation (5 minutes)

### 1. Database Schema
```bash
# Start PostgreSQL container only
docker-compose up postgres -d

# Wait for postgres to be ready (check logs)
docker-compose logs postgres | grep "database system is ready"

# Connect and verify tables
docker exec ecosurvey-postgres-1 psql -U postgres -d ecosurvey -c "\dt"

# Expected output: 19 tables
# corpora, documents, nodes, edges, data_files, data_sheets, data_tables, 
# indicators, indicator_series, topic_briefs, claim_cards, search_index, 
# embeddings, sessions, conversations, messages, retrieval_events, 
# message_labels, topic_clusters, daily_insights, ingestion_runs
```

### 2. SQLAlchemy Models
```bash
# Install backend dependencies
cd backend
pip install -r requirements.txt

# Test model imports
python -c "from app.models import *; print('✓ All models imported successfully')"

# Verify model count
python -c "from app.models import Base; print(f'✓ {len(Base.metadata.tables)} tables mapped')"
```

### 3. API Health Check
```bash
# Start all services
docker-compose up -d

# Wait for backend to start (20 seconds)
sleep 20

# Check health endpoint
curl http://localhost:8000/health

# Expected response
# {"status": "ok", "database": "connected", "timestamp": "..."}
```

### 4. API Documentation
Open browser: http://localhost:8000/docs
- Swagger UI should load
- All 6 routers visible: health, auth, briefing, chat, evidence, admin

### 5. Frontend
Open browser: http://localhost:3000
- Home page loads with navigation
- Summary and Chat links functional
- No JavaScript errors in browser console (F12)

## Detailed Tests

### Database Connection Test
```bash
python -c "
from backend.app.core.database import SessionLocal
from backend.app.core.settings import settings

session = SessionLocal()
result = session.execute('SELECT COUNT(*) FROM corpora')
count = result.scalar()
print(f'✓ Database connected: {count} corpora')
session.close()
"
```

### Model Relationships Test
```bash
cd backend
python << 'EOF'
from app.models import (
    Corpus, Document, Node, Edge, DataFile, DataSheet, DataTable,
    Indicator, IndicatorSeries, TopicBrief, ClaimCard, SearchIndex, Embedding,
    Session, Conversation, Message, RetrievalEvent, MessageLabel,
    TopicCluster, DailyInsight, IngestionRun
)

models = [
    Corpus, Document, Node, Edge, DataFile, DataSheet, DataTable,
    Indicator, IndicatorSeries, TopicBrief, ClaimCard, SearchIndex, Embedding,
    Session, Conversation, Message, RetrievalEvent, MessageLabel,
    TopicCluster, DailyInsight, IngestionRun
]

print(f"✓ {len(models)} models imported")
for model in models:
    print(f"  - {model.__name__}")
EOF
```

### Docker Compose Validation
```bash
# Check service health
docker-compose ps

# Expected: all services healthy
# postgres: healthy
# backend: running
# frontend: running

# Check volumes
docker-compose exec postgres psql -U postgres -l

# Expected: ecosurvey database exists
```

### Environment Configuration Test
```bash
cd backend
python << 'EOF'
from app.core.settings import settings

print("✓ Configuration loaded:")
print(f"  - Database: {settings.database_host}:{settings.database_port}")
print(f"  - Provider: {settings.llm_provider}")
print(f"  - Global Budget: {settings.context_budget_global}")
print(f"  - Mode: {settings.ingestion_mode}")
EOF
```

## Acceptance Criteria

### ✅ Phase 1 Complete When:

1. **Database**
   - [ ] PostgreSQL container starts
   - [ ] 19 tables created with correct schema
   - [ ] pgvector extension enabled
   - [ ] All constraints applied (CHECK, FOREIGN KEY)

2. **Models**
   - [ ] All 19 SQLAlchemy models load
   - [ ] Relationships defined (back_populates, cascade)
   - [ ] UUID primary keys
   - [ ] JSONB columns mapped correctly

3. **API**
   - [ ] FastAPI app starts on port 8000
   - [ ] `/health` endpoint returns 200 OK
   - [ ] `/docs` (Swagger UI) loads
   - [ ] CORS configured correctly
   - [ ] All 6 routers included

4. **Frontend**
   - [ ] index.html loads on port 3000
   - [ ] CSS styling applied
   - [ ] Navigation functional
   - [ ] No JavaScript errors

5. **Docker**
   - [ ] `docker-compose up` starts all 3 services
   - [ ] Services communicate (backend → postgres)
   - [ ] Volumes persist data
   - [ ] Health checks pass

6. **Configuration**
   - [ ] `.env` file loaded
   - [ ] All required variables present
   - [ ] Database URL constructed correctly
   - [ ] LLM provider selected

## Troubleshooting

### Database Won't Start
```bash
# Check PostgreSQL logs
docker-compose logs postgres

# Rebuild container
docker-compose down
docker volume rm ecosurvey_postgres_data
docker-compose up postgres
```

### Backend Connection Timeout
```bash
# Ensure postgres is healthy first
docker-compose up postgres -d
sleep 15

# Then start backend
docker-compose up backend
```

### API Health Check Returns 500
```bash
# Check backend logs
docker-compose logs backend

# Verify .env DATABASE_URL is correct
# Format: postgresql://user:password@host:port/database
```

### Models Import Fails
```bash
# Verify all dependencies installed
cd backend
pip install -r requirements.txt

# Check PostgreSQL client library
pip install psycopg2-binary
```

### CORS Errors in Frontend
```bash
# Edit backend/app/main.py CORS origins to include frontend URL
# Example: http://localhost:3000

# Restart backend
docker-compose restart backend
```

## Performance Checklist

- [ ] Database indexes created (foreign keys, FTS, pgvector)
- [ ] Connection pooling configured
- [ ] API response time < 500ms for health check
- [ ] Frontend loads in < 2 seconds
- [ ] No memory leaks in Docker containers

## Next Steps (Phase 2)

Once Phase 1 passes:
1. Implement Google OAuth in auth.py
2. Create session tracking tables data
3. Test login/logout flow
4. Verify pseudonymous user identification

---

**Estimated Duration:** 15 minutes  
**Success Rate:** 100% if all steps complete  
**Critical Path:** Database → Models → API → Frontend
