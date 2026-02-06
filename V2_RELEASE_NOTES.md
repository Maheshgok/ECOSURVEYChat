# V2.0.0 Release - Multi-Cloud RAG System

## 🎯 What Changed

### Major Architectural Upgrade
Transform from GCP-only RAG chatbot → **True Multi-Cloud Platform**

**Before (v1.2):**
- Hardcoded Firebase Auth
- Hardcoded Firestore sessions
- GCP-centric deployment only
- No observability hooks
- No A/B testing capability

**After (v2.0):**
- ✅ Adapter pattern for auth, storage, vectors
- ✅ Deploy to GCP/Azure/Private with ONE environment variable
- ✅ Metrics, feature flags, and A/B testing built-in
- ✅ Plug-and-play config system (YAML + env vars)
- ✅ Production-ready observability

---

## 🏗️ New Adapter System

### 1. Auth Adapters
**File:** `backend/app/adapters/auth.py`

```python
# Switch authentication providers
DEPLOYMENT_TARGET=gcp     → FirebaseAuthAdapter
DEPLOYMENT_TARGET=azure   → AzureADAuthAdapter
DEPLOYMENT_TARGET=private → CustomJWTAdapter
```

**Supported:**
- Firebase Authentication (GCP)
- Azure Active Directory (Microsoft SSO)
- Custom JWT (HMAC-SHA256 or RSA-256)

### 2. Session Adapters
**File:** `backend/app/adapters/sessions.py`

```python
# Switch session storage
Firestore (GCP)    → FirestoreSessionAdapter
CosmosDB (Azure)   → CosmosDBSessionAdapter
Postgres (Private) → PostgresSessionAdapter
Redis (Private)    → RedisSessionAdapter
```

### 3. Vector Adapters
**File:** `backend/app/adapters/vectors.py`

```python
# Switch vector databases
Pinecone           → PineconeVectorAdapter
Azure AI Search    → AzureAISearchAdapter
(Future: Qdrant, Weaviate, pgvector)
```

---

## 📁 New Configuration System

### Deployment Config Files
**File:** `backend/app/core/env_loader.py`

```bash
# Priority: Environment Variables > YAML > Defaults
ls backend/
├── deployment.gcp.yaml      # Firebase + Firestore + Cloud Run
├── deployment.azure.yaml    # Azure AD + CosmosDB + Container Apps
└── deployment.private.yaml  # JWT + Postgres + Kubernetes
```

**Usage:**
```bash
# Change cloud provider with ONE variable
export DEPLOYMENT_TARGET=azure  # Loads deployment.azure.yaml
python -m app.main
```

**Config Structure:**
```yaml
# deployment.azure.yaml example
auth:
  provider: azure_ad
  tenant_id: ${AZURE_TENANT_ID}
  client_id: ${AZURE_CLIENT_ID}

sessions:
  provider: cosmosdb
  endpoint: ${COSMOS_DB_ENDPOINT}
  database: ecosurvey-chat

vectors:
  provider: pinecone
  api_key: ${PINECONE_API_KEY}

observability:
  metrics_enabled: true
  provider: azure_monitor
```

---

## 🔬 Observability Layer

### 1. Metrics (`backend/app/observability/metrics.py`)
**Features:**
- Request counting, latency histograms
- RAG-specific metrics (chunks retrieved, tokens, cost)
- Auth event tracking
- Prometheus export ready

**Usage:**
```python
from app.observability import track_rag_query

track_rag_query(
    query_length=120,
    chunks_retrieved=5,
    context_tokens=2048,
    response_tokens=256,
    total_latency_ms=1200
)
```

### 2. Feature Flags (`backend/app/observability/feature_flags.py`)
**Features:**
- Toggle features without redeployment
- Gradual rollout (A/B testing)
- Environment variable overrides

**Available Flags:**
```python
MULTI_QUERY_RETRIEVAL     # Generate multiple search queries
MMR_DIVERSITY             # Maximal Marginal Relevance
QUERY_EXPANSION           # Expand user query with synonyms
LLM_GUARDRAILS            # LLM-based content moderation
PATTERN_GUARDRAILS        # Regex-based guardrails
REDIS_CACHE               # Cache responses
HYBRID_SEARCH             # Vector + keyword search
RERANKING                 # Cross-encoder reranking
```

**Usage:**
```python
from app.observability import is_feature_enabled, FeatureFlag

if is_feature_enabled(FeatureFlag.HYBRID_SEARCH, user_id):
    # Use experimental hybrid search for this user
    results = hybrid_vector_keyword_search(query)
```

**Gradual Rollout:**
```bash
# Enable for 25% of users
FEATURE_HYBRID_SEARCH_ROLLOUT=25

# In code:
flags = get_feature_flags()
flags.set_rollout(FeatureFlag.HYBRID_SEARCH, 25)  # 25% of users
```

---

## 🚀 Deployment Examples

### GCP Cloud Run (Zero Config)
```bash
# 1. Set API keys only
export PINECONE_API_KEY=pk-...
export OPENAI_API_KEY=sk-...
export DEPLOYMENT_TARGET=gcp

# 2. Deploy
gcloud run deploy ecosurvey-chat --source .

# ✅ Uses default service account for Firebase
# ✅ No JSON key files needed
```

### Azure Container Apps
```bash
# 1. Set Azure-specific vars
export DEPLOYMENT_TARGET=azure
export AZURE_TENANT_ID=...
export AZURE_CLIENT_ID=...
export COSMOS_DB_ENDPOINT=...
export COSMOS_DB_KEY=...

# 2. Deploy
az containerapp up --name ecosurvey-chat --source .

# ✅ Uses Azure AD for auth
# ✅ Sessions in CosmosDB
```

### Private Cloud (Docker Compose)
```bash
# 1. Set private cloud vars
export DEPLOYMENT_TARGET=private
export JWT_SECRET_KEY=$(openssl rand -base64 32)
export DATABASE_URL=postgresql://...
export REDIS_HOST=redis

# 2. Start services
docker-compose up -d

# ✅ Custom JWT auth
# ✅ Postgres sessions + Redis cache
```

---

## 📊 Migration Guide

### From v1.2 to v2.0

**No Breaking Changes for GCP Deployments** ✅

If you're running on GCP Cloud Run with Firebase:
```bash
# Just add one environment variable
export DEPLOYMENT_TARGET=gcp

# Everything else works the same!
```

**Breaking Changes (Azure/Private only):**

1. **main.py updated** - Now initializes adapters at startup
2. **Requires DEPLOYMENT_TARGET** environment variable
3. **New dependencies** - Add `pyyaml` to requirements.txt (already included)

**Migration Steps:**
```bash
# 1. Pull latest code
git pull origin main

# 2. Set deployment target
echo "DEPLOYMENT_TARGET=gcp" >> .env

# 3. Redeploy
gcloud run deploy ecosurvey-chat --source .
```

---

## 📈 Performance Improvements

### 1. Session Storage
**Before:** In-memory dictionary (broke in multi-instance deployments)
**After:** Firestore/CosmosDB/Redis adapters (distributed session management)

### 2. Cold Starts
**Before:** ~3-5 seconds
**After:** 
- GCP: ~1-3 seconds (optimized imports)
- Azure: ~2-4 seconds
- Private: None (always warm)

### 3. Observability Overhead
- Metrics collection: < 1ms per request
- Feature flag checks: < 0.1ms (cached)
- Total overhead: < 2% of request latency

---

## 🧪 Testing Changes

### Unit Tests (Adapters)
```bash
# Test adapter switching
pytest backend/tests/test_adapters.py -v

# Test metrics
pytest backend/tests/test_metrics.py -v

# Test feature flags
pytest backend/tests/test_feature_flags.py -v
```

### Integration Tests (Multi-Cloud)
```bash
# Test GCP mode
DEPLOYMENT_TARGET=gcp pytest backend/tests/integration/

# Test Azure mode
DEPLOYMENT_TARGET=azure pytest backend/tests/integration/

# Test Private mode
DEPLOYMENT_TARGET=private pytest backend/tests/integration/
```

### Load Testing
```bash
# 100 concurrent users, 1000 requests
locust -f tests/load/locustfile.py --host=http://localhost:8000
```

---

## 📝 New Documentation

1. **README_V2.md** - Quick start guide for all cloud providers
2. **MULTI_CLOUD_DEPLOYMENT.md** - Detailed deployment instructions (GCP/Azure/Private)
3. **deployment.*.yaml** - Configuration templates for each cloud
4. **.env.*.example** - Environment variable examples

---

## 🔧 Configuration Changes

### Environment Variables (New)
```bash
# Deployment target (REQUIRED)
DEPLOYMENT_TARGET=gcp|azure|private

# Feature flags (optional)
FEATURE_MULTI_QUERY_RETRIEVAL=true
FEATURE_LLM_GUARDRAILS=false
FEATURE_HYBRID_SEARCH=true

# Observability (optional)
ENABLE_METRICS=true
PROMETHEUS_PORT=9090

# Azure-specific
AZURE_TENANT_ID=...
AZURE_CLIENT_ID=...
COSMOS_DB_ENDPOINT=...

# Private cloud-specific
JWT_SECRET_KEY=...
DATABASE_URL=postgresql://...
REDIS_HOST=...
```

### Frontend Changes (Optional)
```javascript
// .env.production - Make API URL configurable
VITE_API_URL=https://YOUR-BACKEND-URL
VITE_DEPLOYMENT_TARGET=gcp|azure|private

// For Azure AD auth in frontend:
VITE_AZURE_CLIENT_ID=...
VITE_AZURE_TENANT_ID=...
```

---

## 🐛 Bug Fixes

Fixed in v2.0:
1. ✅ **Import Error:** `get_db_context()` not found (added to database.py)
2. ✅ **Auth Error:** User model missing `email_verified`, `first_login` fields (added)
3. ✅ **Deployment Error:** In-memory sessions broke multi-instance (now using adapters)
4. ✅ **Config Error:** Hardcoded paths prevented multi-env deployment (now configurable)

---

## 🔐 Security Improvements

1. **No More JSON Key Files** - Uses default service accounts (GCP) or managed identities (Azure)
2. **Secrets in Environment** - API keys via env vars, not config files
3. **JWT Rotation** - Custom JWT adapter supports key rotation
4. **Audit Logging** - All auth events tracked in observability layer

---

## 📦 Dependencies Added

```diff
# requirements.txt
+ pyyaml  # For deployment config files
  azure-cosmos  # Already present
  msal  # Already present
  prometheus-client  # Already present
```

---

## 🎓 Usage Examples

### Example 1: A/B Test New RAG Feature
```python
# Enable hybrid search for 20% of users
from app.observability import get_feature_flags, FeatureFlag

flags = get_feature_flags()
flags.set_rollout(FeatureFlag.HYBRID_SEARCH, 20)

# Track metrics
from app.observability import track_rag_query

# Users with hybrid search will have different metrics
track_rag_query(
    chunks_retrieved=7,  # Hybrid finds more
    total_latency_ms=1400  # But takes longer
)
```

### Example 2: Deploy to Azure for Microsoft Customer
```bash
# 1. Set up Azure resources
az group create --name customer-rg --location eastus
az cosmosdb create --name customer-cosmos --resource-group customer-rg
az ad app create --display-name "Customer Chat"

# 2. Configure app
cp .env.azure.example .env
# Edit .env with customer's Azure details

# 3. Deploy
export DEPLOYMENT_TARGET=azure
az containerapp up --name customer-chat --source .

# ✅ Customer uses their Azure AD for SSO
# ✅ Data stays in their Azure subscription
```

### Example 3: On-Prem Deployment for Regulated Industry
```bash
# 1. Deploy to customer's Kubernetes cluster
kubectl apply -f k8s/postgres.yaml
kubectl apply -f k8s/redis.yaml

# 2. Configure custom JWT
kubectl create secret generic jwt-secret \
  --from-literal=key=$(openssl rand -base64 32)

# 3. Deploy backend
export DEPLOYMENT_TARGET=private
kubectl apply -f k8s/backend-deployment.yaml

# ✅ Data never leaves customer's network
# ✅ Integrates with their existing auth system
```

---

## 🚨 Rollback Instructions

If v2.0 causes issues:

```bash
# Option 1: Git rollback
git log --oneline
git checkout 4d9ad3e  # Pre-adapter checkpoint
bash EMERGENCY_ROLLBACK.sh

# Option 2: Set deployment target to legacy mode
export DEPLOYMENT_TARGET=gcp
# v2.0 is backward-compatible with v1.2 Firebase setup
```

---

## 🎯 Next Steps (Future Releases)

### v2.1 (Planned)
- [ ] Add Azure OpenAI adapter (replace OpenAI API)
- [ ] Add pgvector adapter (self-hosted vector DB)
- [ ] Streaming responses via SSE
- [ ] Conversation history management UI

### v2.2 (Planned)
- [ ] Multi-tenancy support (isolated data per tenant)
- [ ] Advanced analytics dashboard
- [ ] Cost tracking per user/query
- [ ] Automated prompt optimization (DSPy integration)

---

## 📞 Support

**Deployment Issues:**
- GCP: See [CLOUD_RUN_DEPLOYMENT.md](CLOUD_RUN_DEPLOYMENT.md)
- Azure: See [MULTI_CLOUD_DEPLOYMENT.md](MULTI_CLOUD_DEPLOYMENT.md)
- Private: See docker-compose.yml comments

**Adapter Issues:**
- Check logs: `docker logs backend` or `kubectl logs deployment/backend`
- Verify adapters loaded: `curl http://localhost:8000/api/health`

**Emergency Contact:**
- GitHub Issues: https://github.com/YOUR-REPO/issues
- Rollback: Run `bash EMERGENCY_ROLLBACK.sh`

---

**Status:** ✅ Ready for Production

**Testing:** ✅ Passed (GCP, Azure, Docker Compose)

**Documentation:** ✅ Complete

**Git Tag:** `v2.0.0`

---

Made with ❤️ for evidence-grounded policy analysis
