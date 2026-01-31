# Phase 1 Deviations from Specification

**Document Purpose:** Track all changes made to the specification for Phase 1 that require correction, rollback, or enhancement in subsequent phases  
**Last Updated:** January 31, 2026  
**Status:** Active - Update as deviations are discovered

---

## Table of Contents

1. [Database Schema Deviations](#database-schema-deviations)
2. [Security Configuration Deviations](#security-configuration-deviations)
3. [API Implementation Deviations](#api-implementation-deviations)
4. [Frontend Deviations](#frontend-deviations)
5. [Data Model Deviations](#data-model-deviations)
6. [Integration Deviations](#integration-deviations)
7. [Correction Timeline](#correction-timeline)
8. [Rollback Procedures](#rollback-procedures)

---

## Database Schema Deviations

### Deviation 1: pgvector Extension Removed

**Status:** ⚠️ Phase 1 Simplification  
**Spec Requirement:** Use pgvector (vector) type for semantic embeddings  
**Phase 1 Implementation:** TEXT type for embeddings (stored as JSON string)  
**File:** `backend/migrations/001_init_phase1.sql`

**Changes Made:**
```sql
-- Spec (original)
CREATE TABLE embeddings (
    id SERIAL PRIMARY KEY,
    node_id INTEGER REFERENCES nodes(id),
    embedding vector(768),  -- pgvector type
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Phase 1 (simplified)
CREATE TABLE embeddings (
    id SERIAL PRIMARY KEY,
    node_id INTEGER REFERENCES nodes(id),
    embedding TEXT,  -- Stored as JSON string
    embedding_model VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Why Changed:** pgvector extension not available in standard PostgreSQL during Docker issues; deferred to Phase 3

**Impact:**
- ❌ Vector similarity search not available in Phase 1-2
- ❌ Semantic search disabled until Phase 3
- ✅ Basic CRUD for embeddings still works
- ✅ Data structure compatible for migration

**Required in Phase 3:**
```sql
-- Phase 3: Install pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Phase 3: Migrate embeddings to proper vector type
ALTER TABLE embeddings 
    ALTER COLUMN embedding TYPE vector(768) USING embedding::vector(768);

-- Phase 3: Add vector index for similarity search
CREATE INDEX ON embeddings USING ivfflat (embedding vector_cosine_ops);
```

**Location Marker:** Search for `-- PHASE 1: TEXT embeddings (convert to pgvector in Phase 3)`

---

### Deviation 2: Full-Text Search Simplified

**Status:** ⚠️ Phase 1 Simplification  
**Spec Requirement:** Advanced full-text search with multiple languages, custom dictionaries  
**Phase 1 Implementation:** Basic indexed search without advanced features  
**File:** `backend/migrations/001_init_phase1.sql`

**Changes Made:**
```sql
-- Spec (original)
CREATE INDEX idx_search_full_text ON search_index 
    USING GIN(to_tsvector('english', search_text));

CREATE TRIGGER update_search_index_ts 
    BEFORE INSERT OR UPDATE ON documents
    FOR EACH ROW
    EXECUTE FUNCTION update_search_index();

-- Phase 1 (simplified)
CREATE INDEX idx_search_text ON search_index(search_text);
-- No trigger or special functions
```

**Why Changed:** Deferred complex search features to Phase 6 when briefing endpoints fully developed

**Impact:**
- ❌ Full-text search with word variations not available
- ❌ Multi-language support not available
- ✅ Basic text search works with LIKE/ILIKE
- ✅ Index exists for performance

**Required in Phase 6:**
```sql
-- Phase 6: Enable full-text search
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Phase 6: Add GIN index for full-text search
CREATE INDEX idx_search_full_text ON search_index 
    USING GIN(to_tsvector('english', search_text));

-- Phase 6: Create trigger for auto-updates
CREATE FUNCTION update_search_index_trigger() RETURNS TRIGGER AS $$
BEGIN
    UPDATE search_index SET search_text = NEW.title || ' ' || NEW.content;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

**Location Marker:** Search for `-- PHASE 1: Basic search index (enhance with FTS in Phase 6)`

---

### Deviation 3: Missing Ingestion Tracking Tables

**Status:** ⚠️ Partial Implementation  
**Spec Requirement:** Complete ingestion workflow tracking  
**Phase 1 Implementation:** Added single `ingestion_runs` table, missing detailed audit  
**File:** `backend/migrations/001_init_phase1.sql`

**Missing Tables:**
```sql
-- These should be added in Phase 3
CREATE TABLE ingestion_logs (
    id SERIAL PRIMARY KEY,
    ingestion_run_id INTEGER REFERENCES ingestion_runs(id),
    event_type VARCHAR(50),  -- parsed, error, completed
    details JSONB,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE ingestion_errors (
    id SERIAL PRIMARY KEY,
    ingestion_run_id INTEGER REFERENCES ingestion_runs(id),
    file_name VARCHAR(255),
    error_message TEXT,
    error_type VARCHAR(100),
    line_number INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE data_file_metadata (
    id SERIAL PRIMARY KEY,
    data_file_id INTEGER REFERENCES data_files(id),
    key VARCHAR(255),
    value TEXT,
    UNIQUE(data_file_id, key)
);
```

**Why Changed:** Phase 1 focuses on basic data structures; detailed ingestion tracking deferred to Phase 3

**Impact:**
- ❌ No detailed ingestion error tracking in Phase 1-2
- ❌ No step-by-step ingestion logs
- ✅ Basic ingestion run status available
- ✅ Tables can be added without schema conflicts

**Required in Phase 3:**
```sql
-- Phase 3: Create detailed ingestion tracking
-- Run: backend/migrations/003_add_ingestion_tracking.sql
```

**Location Marker:** Search for `-- PHASE 1: Basic ingestion_runs (expand in Phase 3)`

---

## Security Configuration Deviations

### Deviation 4: Optional OAuth Fields

**Status:** ⚠️ Phase 1 Exemption  
**Spec Requirement:** Required environment variables for OAuth  
**Phase 1 Implementation:** Optional with defaults  
**File:** `backend/app/core/settings.py`

**Changes Made:**
```python
# Spec (original)
class Settings(BaseSettings):
    GOOGLE_CLIENT_ID: str  # Required
    GOOGLE_CLIENT_SECRET: str  # Required

# Phase 1 (exempted)
class Settings(BaseSettings):
    GOOGLE_CLIENT_ID: Optional[str] = None  # Optional
    GOOGLE_CLIENT_SECRET: Optional[str] = None  # Optional
```

**Why Changed:** Phase 1 doesn't implement OAuth; Phase 2 will handle authentication

**Impact:**
- ✅ App starts without OAuth configuration
- ✅ Health endpoint works in Phase 1
- ❌ OAuth endpoints will fail in Phase 2 until configured
- ❌ Unauthenticated access possible in Phase 1

**Required in Phase 2:**
```python
# Phase 2: Make OAuth fields required again
class Settings(BaseSettings):
    GOOGLE_CLIENT_ID: str  # REQUIRED
    GOOGLE_CLIENT_SECRET: str  # REQUIRED
    
    @field_validator('GOOGLE_CLIENT_ID', 'GOOGLE_CLIENT_SECRET')
    def validate_oauth_fields(cls, v):
        if not v:
            raise ValueError('OAuth credentials required for Phase 2+')
        return v
```

**Location Marker:** Search for `# PHASE 1: Optional for foundation development`

---

### Deviation 5: Default Security Secrets

**Status:** ⚠️ Phase 1 Exemption  
**Spec Requirement:** Generate strong unique secrets, never hardcode  
**Phase 1 Implementation:** Development defaults hardcoded  
**File:** `backend/app/core/settings.py`

**Changes Made:**
```python
# Spec (original)
SESSION_SECRET: str = secrets.token_urlsafe(32)  # Generate unique
SERVER_SALT: str = secrets.token_urlsafe(32)  # Generate unique

# Phase 1 (defaults)
SESSION_SECRET: Optional[str] = "dev_session_secret_phase1_testing"
SERVER_SALT: Optional[str] = "dev_server_salt_phase1_testing"
```

**Why Changed:** Phase 1 development convenience; never for production

**Impact:**
- ✅ Easy local development
- ✅ Consistent dev behavior
- ❌ SECURITY RISK if accidentally deployed
- ❌ Not suitable for production

**Required in Phase 10 (Production Deployment):**
```python
# Phase 10: Generate and secure secrets
def load_secrets_from_vault():
    """Load from environment (set by deployment system)"""
    return {
        'SESSION_SECRET': os.getenv('SESSION_SECRET'),
        'SERVER_SALT': os.getenv('SERVER_SALT'),
    }

# Phase 10: Validate in production
if ENVIRONMENT == 'production':
    assert not SESSION_SECRET.startswith('dev_'), "Do not use dev defaults in production"
    assert len(SESSION_SECRET) >= 32, "Secrets must be sufficiently long"
```

**Security Checklist for Phase 10:**
- [ ] SESSION_SECRET generated with cryptographic randomness
- [ ] SERVER_SALT generated with cryptographic randomness
- [ ] Secrets stored in environment variables only
- [ ] Secrets rotated regularly
- [ ] Old sessions invalidated during rotation
- [ ] Secrets never logged or committed to git

**Location Marker:** Search for `dev_session_secret_phase1_testing` and `dev_server_salt_phase1_testing`

---

### Deviation 6: Debug Mode Enabled by Default

**Status:** ⚠️ Phase 1 Development Setting  
**Spec Requirement:** Debug disabled in production  
**Phase 1 Implementation:** DEBUG=true in .env  
**File:** `.env`

**Changes Made:**
```env
# Spec (production)
DEBUG=false
ENVIRONMENT=production

# Phase 1 (development)
DEBUG=true
ENVIRONMENT=development
```

**Why Changed:** Makes debugging easier in Phase 1; required for development

**Impact:**
- ✅ Detailed error messages in Phase 1
- ✅ Stack traces visible to developers
- ❌ SECURITY RISK if deployed with DEBUG=true
- ❌ Exposes internal structure to attackers

**Required in Phase 10:**
```python
# Phase 10: Strict debug validation
if ENVIRONMENT == 'production':
    assert DEBUG is False, "DEBUG must be False in production"
    
# Phase 10: Hide stack traces in production
@app.exception_handler(Exception)
async def production_exception_handler(request, exc):
    if DEBUG:
        raise exc  # Phase 1-9: Show details
    else:
        return JSONResponse({"error": "Internal server error"})  # Phase 10+
```

**Location Marker:** Search for `DEBUG=true`

---

## API Implementation Deviations

### Deviation 7: OAuth Router Stubbed

**Status:** ⚠️ Placeholder Implementation  
**Spec Requirement:** Full OAuth 2.0 flow with sessions  
**Phase 1 Implementation:** Skeleton only  
**File:** `backend/app/api/auth.py`

**Changes Made:**
```python
# Spec (original)
@router.post("/auth/google")
def google_login(request: GoogleAuthRequest):
    # Validate token with Google
    # Create user session
    # Return session token
    pass

@router.post("/auth/logout")
def logout(session_token: str):
    # Invalidate session
    # Clear user context
    pass

# Phase 1 (stubbed)
@router.post("/auth/google")
def google_login(request: GoogleAuthRequest):
    """
    PHASE 1: Stub only
    PHASE 2: Implement full OAuth flow
    """
    raise NotImplementedError("OAuth in Phase 2")
```

**Why Changed:** Phase 1 focuses on foundation; OAuth implementation in Phase 2

**Implementation Details for Phase 2:**
```python
# Phase 2 Implementation checklist
# [ ] Validate Google ID tokens
# [ ] Create pseudonymous user sessions
# [ ] Generate session tokens
# [ ] Store session metadata
# [ ] Implement logout flow
# [ ] Add session refresh
# [ ] Validate token on protected endpoints
# [ ] Rate limit auth endpoints
```

**Location Marker:** Search for `PHASE 1: Stub only` in auth.py

---

### Deviation 8: Chat Endpoints Stubbed

**Status:** ⚠️ Placeholder Implementation  
**Spec Requirement:** Full chat interface with message persistence  
**Phase 1 Implementation:** Skeleton only  
**File:** `backend/app/api/chat.py`

**Changes Made:**
```python
# Spec (original)
@router.post("/chat/message")
def send_message(message: ChatMessage, session_id: str):
    # Store message in database
    # Retrieve relevant evidence
    # Generate LLM response
    # Return to user
    pass

# Phase 1 (stubbed)
@router.post("/chat/message")
def send_message(message: ChatMessage, session_id: str):
    """
    PHASE 1: Stub only
    PHASE 7: Implement with LLM integration
    """
    raise NotImplementedError("Chat in Phase 7")
```

**Why Changed:** Phase 1 focuses on data layer; chat implementation in Phase 7

**Implementation Details for Phase 7:**
```python
# Phase 7 Implementation checklist
# [ ] Implement message storage
# [ ] Add message retrieval by session
# [ ] Integrate LLM service
# [ ] Implement context window management
# [ ] Add evidence retrieval from database
# [ ] Generate and cache responses
# [ ] Add response streaming
# [ ] Implement message editing/deletion
```

**Location Marker:** Search for `PHASE 7: Implement` in chat.py

---

### Deviation 9: Briefing Router Stubbed

**Status:** ⚠️ Placeholder Implementation  
**Spec Requirement:** Executive summary generation from data  
**Phase 1 Implementation:** Skeleton only  
**File:** `backend/app/api/briefing.py`

**Changes Made:**
```python
# Spec (original)
@router.get("/briefing/summary")
def get_summary(topic: str, limit: int = 10):
    # Retrieve topic claims
    # Summarize claim evidence
    # Generate executive summary
    # Return formatted briefing
    pass

# Phase 1 (stubbed)
@router.get("/briefing/summary")
def get_summary(topic: str, limit: int = 10):
    """
    PHASE 1: Stub only
    PHASE 6: Implement briefing generation
    """
    raise NotImplementedError("Briefing in Phase 6")
```

**Why Changed:** Phase 1 focuses on data storage; briefing logic in Phase 6

**Implementation Details for Phase 6:**
```python
# Phase 6 Implementation checklist
# [ ] Query claim cards by topic
# [ ] Aggregate evidence by claim
# [ ] Calculate claim strength metrics
# [ ] Generate summary text
# [ ] Format as executive briefing
# [ ] Add citation formatting
# [ ] Implement caching
# [ ] Add PDF export
```

**Location Marker:** Search for `PHASE 6: Implement` in briefing.py

---

## Frontend Deviations

### Deviation 10: Frontend Not Integrated

**Status:** ⚠️ Static Templates Only  
**Spec Requirement:** Full interactive frontend with real-time updates  
**Phase 1 Implementation:** Static HTML/CSS/JavaScript templates  
**Files:** `frontend/index.html`, `frontend/chat.html`, `frontend/summary.html`

**Changes Made:**
```javascript
// Spec (original)
// Real API calls to backend
fetch('/api/chat/message', {
    method: 'POST',
    body: JSON.stringify(message)
}).then(response => response.json());

// Phase 1 (frontend not integrated)
// Frontend exists but not connected to backend
// Uses placeholder data
// No actual API calls

// JavaScript files: app.js, chat.js, summary.js
// Currently: Initialization only, no functionality
```

**Why Changed:** Phase 1 focuses on backend API; frontend integration in Phase 9

**Frontend Integration Timeline:**
- Phase 1-8: Backend features developed
- Phase 9: Connect frontend to real API endpoints
- Phase 10: Deploy frontend

**Implementation Details for Phase 9:**
```javascript
// Phase 9: Enable real API calls
// [ ] Implement authentication flow
// [ ] Add API call utilities
// [ ] Implement real-time chat
// [ ] Add WebSocket for live updates
// [ ] Implement session management
// [ ] Add error handling and retry logic
// [ ] Implement caching strategy
// [ ] Add accessibility features
// [ ] Implement responsive design
```

**Location Marker:** Search for `TODO: Phase 9 - Connect to real API` in frontend JavaScript files

---

### Deviation 11: No User Interface Features

**Status:** ⚠️ Placeholder UI  
**Spec Requirement:** Functional UI with all advertised features  
**Phase 1 Implementation:** HTML structure only, no interactivity  
**File:** `frontend/`

**Missing Features:**
- ❌ Real-time chat interface
- ❌ Message history display
- ❌ Executive briefing display
- ❌ Search functionality
- ❌ User profile
- ❌ Settings page
- ❌ Notification system

**Required in Phase 9:**
```html
<!-- Phase 9: Interactive elements -->
<!-- These elements exist but are not functional -->
<div id="chat-input" class="chat-input">
    <!-- PHASE 9: Connect to backend API -->
    <!-- PHASE 9: Implement real-time message sending -->
</div>

<div id="briefing-display" class="briefing">
    <!-- PHASE 9: Load briefing from /api/briefing/summary -->
    <!-- PHASE 9: Implement briefing refresh -->
</div>
```

**Location Marker:** Search for `PHASE 9` in frontend HTML/JavaScript files

---

## Data Model Deviations

### Deviation 12: Simplified Indicator Models

**Status:** ⚠️ Partial Implementation  
**Spec Requirement:** Complex indicator relationships and time series  
**Phase 1 Implementation:** Basic indicator storage without relationships  
**File:** `backend/app/models/__init__.py`

**Changes Made:**
```python
# Spec (original - complex relationships)
class Indicator(Base):
    __tablename__ = 'indicators'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    definition = Column(Text)
    units = Column(String(50))
    temporal_resolution = Column(String(50))  # Daily, Monthly, Yearly
    geographic_coverage = Column(String(255))
    data_source = Column(String(255))
    
    # Complex relationships
    series = relationship("IndicatorSeries", back_populates="indicator")
    methodology = relationship("IndicatorMethodology")
    constraints = relationship("IndicatorConstraint")

# Phase 1 (simplified)
class Indicator(Base):
    __tablename__ = 'indicators'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    unit = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

**Why Changed:** Phase 1 focuses on basic data structure; complex relationships in Phase 5

**Missing in Phase 1:**
- Temporal resolution tracking
- Geographic coverage mapping
- Data source relationships
- Indicator methodology
- Data constraints and validity rules
- Indicator versioning

**Required in Phase 5:**
```python
# Phase 5: Add complex indicator models
class IndicatorMethodology(Base):
    """Add methodology tracking"""
    pass

class IndicatorConstraint(Base):
    """Add data validity constraints"""
    pass

class IndicatorVersion(Base):
    """Add version history"""
    pass

# Phase 5: Enhance Indicator model
Indicator.methodology = relationship("IndicatorMethodology")
Indicator.constraints = relationship("IndicatorConstraint")
Indicator.versions = relationship("IndicatorVersion")
```

**Location Marker:** Search for `# PHASE 1: Simplified model` in models

---

### Deviation 13: Basic Node/Edge Structure

**Status:** ⚠️ Simplified Relationships  
**Spec Requirement:** Complex graph relationships with weights and types  
**Phase 1 Implementation:** Basic edge storage  
**File:** `backend/app/models/__init__.py`

**Changes Made:**
```python
# Spec (original - typed graph)
class Edge(Base):
    __tablename__ = 'edges'
    
    id = Column(Integer, primary_key=True)
    source_node_id = Column(Integer, ForeignKey('nodes.id'), nullable=False)
    target_node_id = Column(Integer, ForeignKey('nodes.id'), nullable=False)
    edge_type = Column(String(50), nullable=False)  # supports, contradicts, extends
    weight = Column(Float, default=1.0)  # Relationship strength
    confidence = Column(Float, default=0.0)  # Evidence confidence
    bidirectional = Column(Boolean, default=False)
    metadata = Column(JSONB)

# Phase 1 (simplified)
class Edge(Base):
    __tablename__ = 'edges'
    
    id = Column(Integer, primary_key=True)
    source_node_id = Column(Integer, ForeignKey('nodes.id'), nullable=False)
    target_node_id = Column(Integer, ForeignKey('nodes.id'), nullable=False)
    relationship_type = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
```

**Why Changed:** Phase 1 focuses on basic graph structure; complex relationships in Phase 6+

**Missing in Phase 1:**
- Edge weights
- Confidence scores
- Typed relationships (supports/contradicts/extends)
- Bidirectional relationships
- Relationship metadata

**Required in Phase 6+:**
```python
# Phase 6: Enhance Edge model
Edge.weight = Column(Float, default=1.0)
Edge.confidence = Column(Float, default=0.0)
Edge.edge_type = Column(String(50))  # typed relationships
Edge.bidirectional = Column(Boolean, default=False)
Edge.metadata = Column(JSONB)
```

**Location Marker:** Search for `# PHASE 1: Basic relationship` in models

---

## Integration Deviations

### Deviation 14: No Data Ingestion Pipeline

**Status:** ⚠️ Not Implemented  
**Spec Requirement:** Full data ingestion from Excel, PDF, CSV  
**Phase 1 Implementation:** Database schema only  
**File:** `backend/ingestion/` (empty)

**Why Changed:** Phase 1 focuses on API infrastructure; ingestion in Phase 3-5

**What's Missing:**
- ❌ Excel file parser
- ❌ PDF extraction
- ❌ CSV processor
- ❌ Data validation
- ❌ Error recovery
- ❌ Batch processing
- ❌ Progress tracking

**Required in Phase 3:**
```python
# Phase 3: Create ingestion module structure
backend/ingestion/
├── __init__.py
├── parsers/
│   ├── excel_parser.py
│   ├── pdf_parser.py
│   └── csv_parser.py
├── validators.py
├── processors.py
└── tasks.py
```

**Implementation Checklist for Phase 3-5:**
- [ ] Phase 3: Excel file parsing
- [ ] Phase 3: Data validation framework
- [ ] Phase 4: PDF extraction
- [ ] Phase 4: CSV processing
- [ ] Phase 5: LLM-assisted data extraction

---

### Deviation 15: No LLM Integration

**Status:** ⚠️ Not Implemented  
**Spec Requirement:** OpenAI API integration for summaries and chat  
**Phase 1 Implementation:** Placeholder only  
**File:** `backend/app/services/` (llm_service.py stubbed)

**Why Changed:** Phase 1 focuses on data layer; LLM integration in Phase 7

**What's Missing:**
- ❌ OpenAI API client
- ❌ Prompt templates
- ❌ Context window management
- ❌ Token counting
- ❌ Response caching
- ❌ Error handling
- ❌ Cost tracking

**Required in Phase 7:**
```python
# Phase 7: LLM service implementation
backend/app/services/llm_service.py
├── OpenAI client initialization
├── Prompt template management
├── Context window management
├── Response streaming
├── Error recovery
└── Cost tracking
```

**Implementation Checklist for Phase 7:**
- [ ] Initialize OpenAI client
- [ ] Create prompt templates
- [ ] Implement context retrieval
- [ ] Add token counting
- [ ] Implement streaming responses
- [ ] Add response caching
- [ ] Implement rate limiting

---

### Deviation 16: No Analytics System

**Status:** ⚠️ Not Implemented  
**Spec Requirement:** Usage tracking and insights  
**Phase 1 Implementation:** Database schema only  
**File:** `backend/app/api/admin.py` (stubbed)

**Why Changed:** Phase 1 focuses on core functionality; analytics in Phase 8

**What's Missing:**
- ❌ Event tracking
- ❌ Usage metrics
- ❌ User insights
- ❌ Query analytics
- ❌ Dashboard endpoints
- ❌ Report generation
- ❌ Alert system

**Required in Phase 8:**
```python
# Phase 8: Analytics system
backend/app/services/analytics.py
├── Event tracking
├── Metrics aggregation
├── Dashboard data
└── Report generation
```

---

## Correction Timeline

### Phase 2 (OAuth)
- [ ] Revert OAuth fields to required (Deviation 4)
- [ ] Implement Google OAuth flow (Deviation 7)
- [ ] Add session token generation
- [ ] Implement session validation middleware

### Phase 3 (Data Ingestion)
- [ ] Implement Excel file parser (Deviation 14)
- [ ] Add data validation (Deviation 14)
- [ ] Expand ingestion_runs table (Deviation 3)
- [ ] Create ingestion logging tables (Deviation 3)

### Phase 4 (PDF & Advanced Ingestion)
- [ ] Implement PDF extraction (Deviation 14)
- [ ] Implement CSV processing (Deviation 14)
- [ ] Add batch processing

### Phase 5 (Summaries & Indicators)
- [ ] Enhance Indicator model (Deviation 12)
- [ ] Add complex relationships
- [ ] Implement summary generation logic

### Phase 6 (Briefing API)
- [ ] Implement briefing endpoint (Deviation 9)
- [ ] Add full-text search (Deviation 2)
- [ ] Enhance Edge relationships (Deviation 13)
- [ ] Implement briefing generation logic

### Phase 7 (Chat & Evidence)
- [ ] Implement chat endpoints (Deviation 8)
- [ ] Integrate LLM service (Deviation 15)
- [ ] Implement evidence retrieval
- [ ] Add message persistence

### Phase 8 (Analytics)
- [ ] Implement analytics system (Deviation 16)
- [ ] Add event tracking
- [ ] Create dashboard endpoints
- [ ] Generate insights

### Phase 9 (Frontend Integration)
- [ ] Connect frontend to real API (Deviation 10)
- [ ] Implement real-time chat (Deviation 11)
- [ ] Add WebSocket support
- [ ] Implement session management

### Phase 10 (Deployment)
- [ ] Disable debug mode (Deviation 6)
- [ ] Generate secure secrets (Deviation 5)
- [ ] Configure production database
- [ ] Enable pgvector for production (Deviation 1)
- [ ] Deploy to GCP/Netlify

---

## Rollback Procedures

### Rollback Deviation 1: Enable pgvector

**When:** Phase 3 database migration  
**Procedure:**

```sql
-- 1. Install pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Backup embeddings table
CREATE TABLE embeddings_backup AS SELECT * FROM embeddings;

-- 3. Migrate embeddings to vector type
ALTER TABLE embeddings 
    ADD COLUMN embedding_vector vector(768);

UPDATE embeddings 
SET embedding_vector = embedding::vector(768) 
WHERE embedding IS NOT NULL;

-- 4. Drop old column
ALTER TABLE embeddings DROP COLUMN embedding;
ALTER TABLE embeddings RENAME COLUMN embedding_vector TO embedding;

-- 5. Create vector index
CREATE INDEX idx_embedding_search ON embeddings 
    USING ivfflat (embedding vector_cosine_ops);

-- 6. Verify migration
SELECT COUNT(*) as total_embeddings, 
       SUM(CASE WHEN embedding IS NOT NULL THEN 1 ELSE 0 END) as vectors_populated
FROM embeddings;
```

**Validation:**
```python
# Test similarity search
from backend.app.core.database import SessionLocal
session = SessionLocal()

# Should work after migration
results = session.query(Embeddings).filter(
    Embeddings.embedding.cosine_distance(query_vector) < 0.5
).all()

assert len(results) > 0, "Vector search not working"
```

---

### Rollback Deviation 4: Require OAuth

**When:** Phase 2 authentication implementation  
**Procedure:**

```python
# app/core/settings.py

# Before (Phase 1)
GOOGLE_CLIENT_ID: Optional[str] = None

# After (Phase 2)
GOOGLE_CLIENT_ID: str  # Required

# Add validation
@field_validator('GOOGLE_CLIENT_ID', 'GOOGLE_CLIENT_SECRET')
def validate_oauth(cls, v):
    if not v or not v.startswith('dev_'):  # Phase 1 override
        if not v:
            raise ValueError('GOOGLE_CLIENT_ID required in Phase 2+')
    return v
```

**Procedure:**
1. Ensure `.env` has GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET
2. Update settings.py to make fields required
3. Add validation decorator
4. Test: `python -c "from app.core.settings import settings"`
5. Verify OAuth endpoints work

---

### Rollback Deviation 5: Secure Secrets

**When:** Phase 10 production deployment  
**Procedure:**

```bash
# 1. Generate new secrets
python -c "import secrets; print(secrets.token_urlsafe(32))"

# 2. Set in environment
export SESSION_SECRET="<generated_value>"
export SERVER_SALT="<generated_value>"

# 3. Update settings.py
SESSION_SECRET: str = os.getenv("SESSION_SECRET")  # No default
SERVER_SALT: str = os.getenv("SERVER_SALT")  # No default

# 4. Add validation
if not SESSION_SECRET or SESSION_SECRET.startswith("dev_"):
    raise ValueError("Production requires real SESSION_SECRET")

# 5. Deploy
# Secrets set in GCP Secret Manager
```

---

### Rollback Deviation 6: Disable Debug

**When:** Phase 10 production deployment  
**Procedure:**

```bash
# .env (production)
ENVIRONMENT=production
DEBUG=false

# app/core/settings.py
if ENVIRONMENT == 'production':
    assert not DEBUG, "DEBUG must be False in production"
    assert not ENVIRONMENT.startswith('dev'), "Wrong environment"
```

**Validation:**
```powershell
# Before deployment, verify
python -c "from app.core.settings import settings; assert not settings.DEBUG; print('✓ Debug disabled')"
```

---

## Deviation Tracking Template

**When documenting new deviations:**

```markdown
### Deviation N: [Title]

**Status:** ⚠️ Phase X Exemption / Partial Implementation / Not Implemented  
**Spec Requirement:** [What spec says]  
**Phase X Implementation:** [What was actually done]  
**File:** [Where it is]

**Changes Made:**
[Code diff showing changes]

**Why Changed:** [Reasoning for deferral]

**Impact:**
- ❌ What doesn't work
- ✅ What still works

**Required in Phase Y:**
[What needs to be fixed and when]

**Location Marker:** Search for `[unique text in code]`
```

---

## Summary

**Total Deviations:** 16  
**Phase 1 Exemptions:** 6 (Deviations 4, 5, 6, 10, 11, 13)  
**Partial Implementations:** 4 (Deviations 2, 3, 12, 13)  
**Not Implemented:** 6 (Deviations 7, 8, 9, 14, 15, 16)

**Correction Load by Phase:**
- Phase 2: 1 major (OAuth)
- Phase 3: 3 major (Ingestion)
- Phase 4: 1 major (PDF/CSV)
- Phase 5: 2 major (Indicators, Data Model)
- Phase 6: 3 major (Briefing, FTS, Edges)
- Phase 7: 2 major (Chat, LLM)
- Phase 8: 1 major (Analytics)
- Phase 9: 2 major (Frontend, UI)
- Phase 10: 2 major (Security, Production)

**Estimated Effort:** 2-3 hours per deviation correction

---

*Document Created: January 31, 2026*  
*Status: Active*  
*Next Review: After Phase 2 completion*  
*Maintainer: Development Team*

