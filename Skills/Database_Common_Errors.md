# Common Errors: Database Skills (Phase 1)

---

## Error 1: pgvector Extension Not Found

**Symptom:**
```
ERROR: extension "pgvector" does not exist
```

**Cause:** Using standard Postgres image instead of pgvector-enabled image

**Solution:**
```yaml
# In docker-compose.yml, use:
postgres:
  image: pgvector/pgvector:pg15  # NOT postgres:15
```

---

## Error 2: Tables Not Created on Startup

**Symptom:**
```
psql: relation "corpora" does not exist
```

**Cause:** Migration SQL not mounted or not executed

**Solution:**
```yaml
# Ensure this line in docker-compose.yml:
volumes:
  - ./backend/migrations:/docker-entrypoint-initdb.d
```

**Note:** Docker only runs init scripts on FIRST container creation.

**Force re-init:**
```bash
docker-compose down -v  # Removes volumes
docker-compose up -d
```

---

## Error 3: SQLAlchemy Import Errors

**Symptom:**
```python
ImportError: cannot import name 'JSON' from 'sqlalchemy'
```

**Cause:** Wrong SQLAlchemy version or missing imports

**Solution:**
```python
# For JSONB columns:
from sqlalchemy.dialects.postgresql import JSONB

# For vector columns:
from pgvector.sqlalchemy import Vector

# Example:
metadata = Column(JSONB)
embedding = Column(Vector(1536))
```

---

## Error 4: Database Connection Refused

**Symptom:**
```
sqlalchemy.exc.OperationalError: could not connect to server
```

**Cause:** Postgres not ready when API starts

**Solution 1:** Add depends_on with healthcheck
```yaml
api:
  depends_on:
    postgres:
      condition: service_healthy
  
postgres:
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U postgres"]
    interval: 5s
    timeout: 5s
    retries: 5
```

**Solution 2:** Add retry logic in `database.py`
```python
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
import time

def create_engine_with_retry(url, retries=5, delay=2):
    for attempt in range(retries):
        try:
            engine = create_engine(url)
            engine.connect()  # Test connection
            return engine
        except OperationalError:
            if attempt < retries - 1:
                time.sleep(delay)
            else:
                raise
```

---

## Error 5: Migration SQL Syntax Errors

**Symptom:**
```
ERROR: syntax error at or near "JSONB"
```

**Cause:** Invalid SQL syntax or missing type

**Solution:**
- Test migration file directly:
```bash
docker-compose exec postgres psql -U postgres -d survey_chat -f /docker-entrypoint-initdb.d/001_init.sql
```
- Fix syntax errors
- Common fixes:
  - Use `JSONB` not `JSON` for better performance
  - Use `TEXT` not `VARCHAR` for unlimited strings
  - Use `TIMESTAMPTZ` not `TIMESTAMP` for timezone support

---

## Error 6: Foreign Key Constraint Violations

**Symptom:**
```
ERROR: insert or update on table "nodes" violates foreign key constraint
```

**Cause:** Inserting child record before parent exists

**Solution:**
- Ensure tables created in correct order (parents first)
- In migration file:
```sql
-- Parent tables first
CREATE TABLE corpora (...);
CREATE TABLE documents (...);

-- Then child tables
CREATE TABLE nodes (
    ...
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE
);
```

---

## Error 7: Index Creation Failures

**Symptom:**
```
ERROR: could not create index "idx_embeddings_vector"
ERROR: data type vector has no default operator class
```

**Cause:** Missing pgvector extension or wrong index syntax

**Solution:**
```sql
-- Create extension first
CREATE EXTENSION IF NOT EXISTS vector;

-- Then create index with proper operator class
CREATE INDEX idx_embeddings_vector ON embeddings USING ivfflat (embedding vector_cosine_ops);
```

---

## Error 8: Pydantic Settings Not Loading

**Symptom:**
```
ValidationError: 1 validation error for Settings
DATABASE_URL
  field required
```

**Cause:** `.env` file not found or not loaded

**Solution:**
```python
# In config.py:
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# Ensure .env file exists in backend/ directory
```

---

## Error 9: Port Already in Use

**Symptom:**
```
Error starting userland proxy: listen tcp4 0.0.0.0:5432: bind: address already in use
```

**Cause:** Local Postgres already running on port 5432

**Solution 1:** Stop local Postgres
```bash
# Windows
net stop postgresql-x64-15

# Linux/Mac
sudo systemctl stop postgresql
```

**Solution 2:** Change port in docker-compose.yml
```yaml
postgres:
  ports:
    - "5433:5432"  # Map to different host port
```

Then update DATABASE_URL:
```
DATABASE_URL=postgresql://postgres:postgres@localhost:5433/survey_chat
```

---

## Error 10: Model Relationships Not Working

**Symptom:**
```
AttributeError: 'Corpus' object has no attribute 'documents'
```

**Cause:** SQLAlchemy relationships not defined

**Solution:**
```python
from sqlalchemy.orm import relationship

class Corpus(Base):
    __tablename__ = "corpora"
    id = Column(Integer, primary_key=True)
    
    # Define relationship
    documents = relationship("Document", back_populates="corpus")

class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True)
    corpus_id = Column(Integer, ForeignKey("corpora.id"))
    
    # Back reference
    corpus = relationship("Corpus", back_populates="documents")
```

---

## Error 11: CORS Errors in Browser

**Symptom:**
```
Access to XMLHttpRequest blocked by CORS policy
```

**Cause:** Frontend domain not in allowed origins

**Solution:**
```python
# In main.py:
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://your-netlify-site.netlify.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## Error 12: Docker Build Failures

**Symptom:**
```
ERROR: Could not find a version that satisfies the requirement fastapi
```

**Cause:** Network issues or wrong package names

**Solution:**
```dockerfile
# Use --no-cache-dir and specify versions
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Or use multi-stage build with caching
FROM python:3.11-slim as builder
WORKDIR /app
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /app/wheels -r requirements.txt

FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /app/wheels /wheels
RUN pip install --no-cache-dir /wheels/*
```

---

## Error 13: Alembic vs Raw SQL Confusion

**Note:** This project uses **raw SQL migrations**, not Alembic.

**If you accidentally installed Alembic:**
- Remove from requirements.txt
- Delete alembic/ directory
- Use only `migrations/*.sql` files

**Migration execution:**
- Docker auto-runs `/docker-entrypoint-initdb.d/*.sql` on first start
- For manual execution:
```bash
docker-compose exec postgres psql -U postgres -d survey_chat -f /path/to/migration.sql
```

---

## 🔍 Debugging Checklist

When Phase 1 tests fail:

1. **Check Docker logs:**
   ```bash
   docker-compose logs postgres
   docker-compose logs api
   ```

2. **Verify database:**
   ```bash
   docker-compose exec postgres psql -U postgres -d survey_chat
   ```
   ```sql
   \dt  -- List tables
   \d corpora  -- Describe table
   SELECT count(*) FROM corpora;
   ```

3. **Test API independently:**
   ```bash
   curl -v http://localhost:8000/api/health
   ```

4. **Check Python imports:**
   ```bash
   docker-compose exec api python -c "from app.models import corpus; print('OK')"
   ```

5. **Validate environment variables:**
   ```bash
   docker-compose exec api env | grep DATABASE_URL
   ```

---

## ⚠️ Stop Condition Checks

Phase 1 has no explicit stop conditions, but ensure:

- ✅ No hardcoded credentials in code (use .env)
- ✅ No extra fields beyond spec in models
- ✅ No Alembic or other ORM migration tools (raw SQL only)
- ✅ Timestamps use timezone-aware types (TIMESTAMPTZ)

---

## 📞 When to Escalate

Escalate if:
- pgvector extension cannot be installed after trying pgvector/pgvector image
- Docker networking issues persist across multiple environments
- SQLAlchemy version conflicts cannot be resolved
- Database design conflicts with spec requirements (escalate before changing schema)
