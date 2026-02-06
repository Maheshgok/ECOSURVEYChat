# Economic Survey Chat v2.0 - Multi-Cloud RAG System

**Plug-and-Play RAG Chatbot** - Deploy to GCP, Azure, or Private Cloud with minimal config changes.

## 🚀 Quick Start (Choose Your Cloud)

### Option 1: GCP Cloud Run (Zero Config)
```bash
# 1. Set environment variables
cp .env.gcp.example .env
# Edit .env - only PINECONE_API_KEY and OPENAI_API_KEY required

# 2. Deploy
gcloud run deploy ecosurvey-chat --source .

# ✅ Uses Firebase Auth + Firestore (automatic in Cloud Run)
```

### Option 2: Azure Container Apps
```bash
# 1. Set environment variables
cp .env.azure.example .env
# Edit .env - set AZURE_TENANT_ID, COSMOS_DB_ENDPOINT, etc.

# 2. Set DEPLOYMENT_TARGET
export DEPLOYMENT_TARGET=azure

# 3. Deploy
az containerapp up --name ecosurvey-chat --source .

# ✅ Uses Azure AD + CosmosDB
```

### Option 3: Private Cloud / Kubernetes
```bash
# 1. Set environment variables
cp .env.private.example .env
# Edit .env - set JWT_SECRET_KEY, DATABASE_URL, REDIS_HOST, etc.

# 2. Set DEPLOYMENT_TARGET
export DEPLOYMENT_TARGET=private

# 3. Deploy with Docker Compose
docker-compose up -d

# OR Deploy to Kubernetes
kubectl create configmap ecosurvey-config --from-env-file=.env
kubectl apply -f k8s/

# ✅ Uses Custom JWT + Postgres + Redis
```

## 🏗️ Architecture

### Adapter Pattern (Multi-Cloud Abstraction)

```
┌─────────────────────────────────────────────────────────┐
│                    FastAPI Backend                       │
├─────────────────────────────────────────────────────────┤
│  Auth Adapter    │  Session Adapter  │  Vector Adapter  │
├──────────────────┼───────────────────┼──----------------┤
│ • Firebase       │ • Firestore       │ • Pinecone       │
│ • Azure AD       │ •CosmosDB        │ • Azure AI Search│
│ • Custom JWT     │ • Postgres        │ • (Hybrid)       │
│                  │ • Redis           │                  │
└──────────────────┴───────────────────┴──────────────────┘
```

### Configuration Priority

1. **Environment Variables** (highest)
2. **deployment.{target}.yaml file** (medium)
3. **Built-in defaults** (lowest)

Example: Set `DEPLOYMENT_TARGET=azure` → app loads `deployment.azure.yaml` → overrides with env vars

## 📁 Project Structure

```
backend/
├── app/
│   ├── adapters/           # Multi-cloud adapters
│   │   ├── auth.py         # Firebase/Azure AD/JWT
│   │   ├── sessions.py     # Firestore/CosmosDB/Postgres/Redis
│   │   └── vectors.py      # Pinecone/Azure AI Search
│   ├── api/                # FastAPI endpoints
│   │   └── rag_chat_v2.py  # Main chat endpoint
│   ├── core/
│   │   ├── env_loader.py   # Config loader (YAML + env vars)
│   │   └── settings.py     # Base settings
│   ├── observability/
│   │   ├── metrics.py      # Prometheus/CloudWatch metrics
│   │   └── feature_flags.py# A/B testing toggles
│   └── services/
│       └── conversational_rag.py  # RAG logic
├── deployment.gcp.yaml     # GCP config
├── deployment.azure.yaml   # Azure config
└── deployment.private.yaml # Private cloud config
```

## 🔧 Configuration Examples

### GCP (Firebase + Firestore)
```yaml
# deployment.gcp.yaml (already configured)
auth:
  provider: firebase
sessions:
  provider: firestore
vectors:
  provider: pinecone
```

### Azure (Azure AD + CosmosDB)
```yaml
# deployment.azure.yaml (already configured)
auth:
  provider: azure_ad
  tenant_id: ${AZURE_TENANT_ID}
sessions:
  provider: cosmosdb
  endpoint: ${COSMOS_DB_ENDPOINT}
vectors:
  provider: pinecone  # Or azure_ai_search
```

### Private (JWT + Postgres + Redis)
```yaml
# deployment.private.yaml (already configured)
auth:
  provider: custom_jwt
  secret_key: ${JWT_SECRET_KEY}
sessions:
  provider: redis  # Or postgres
  host: ${REDIS_HOST}
vectors:
  provider: pinecone
```

## 🧪 A/B Testing & Feature Flags

Control features via environment variables:

```bash
# Enable/disable features
FEATURE_MULTI_QUERY_RETRIEVAL=true
FEATURE_MMR_DIVERSITY=true
FEATURE_LLM_GUARDRAILS=false  # Disabled for performance
FEATURE_REDIS_CACHE=true
FEATURE_HYBRID_SEARCH=true

# Gradual rollout (50% of users)
python -c "from app.observability import get_feature_flags; \
           flags = get_feature_flags(); \
           flags.set_rollout('hybrid_search', 50)"
```

In code:
```python
from app.observability import is_feature_enabled, FeatureFlag

if is_feature_enabled(FeatureFlag.HYBRID_SEARCH, user_id):
    # Use hybrid vector + keyword search
    pass
```

## 📊 Metrics & Monitoring

### Prometheus (Private Cloud)
```python
from app.observability import track_rag_query

track_rag_query(
    query_length=len(query),
    chunks_retrieved=5,
    context_tokens=2000,
    response_tokens=300,
    total_latency_ms=1200.5
)
```

Access metrics at `/metrics` endpoint.

### Azure Application Insights
Set `APPLICATIONINSIGHTS_CONNECTION_STRING` in `.env.azure`

### GCP Cloud Monitoring
Auto-configured in Cloud Run (logs, traces, metrics)

## 🔐 Authentication

### Firebase (GCP)
Frontend sends Firebase ID token → Backend verifies with Firebase Admin SDK

### Azure AD (Azure)
Frontend uses MSAL.js → Backend verifies JWT with Azure AD public keys

### Custom JWT (Private)
Generate tokens with your auth service → Backend verifies with shared secret or public key

```bash
# Generate JWT secret
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## 🛠️ Development

### Local Setup
```bash
# 1. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r backend/requirements.txt

# 3. Set environment
cp .env.gcp.example .env
# Edit .env with your keys

# 4. Run locally
cd backend
python -m app.main
```

### Run with Docker
```bash
docker-compose up -d
```

### Run Tests
```bash
pytest backend/tests/
```

## 📦 Requirements

**Core:**
- Python 3.11+
- FastAPI 0.x
- OpenAI API key
- Pinecone API key (or Azure AI Search)

**Cloud-Specific:**

**GCP:** Firebase project (free tier OK)
**Azure:** Azure subscription, AD tenant, CosmosDB account
**Private:** Postgres 15+, Redis 7+ (optional), Kubernetes/Docker

## 🚨 Troubleshooting

### Import Errors
```bash
# If you see "get_db_context() not found":
git log --oneline -1  # Should show "4d9ad3e Pre-adapter cleanup checkpoint"
# If not, run: bash EMERGENCY_ROLLBACK.sh
```

### Auth Failures
```bash
# Verify adapter loaded
curl http://localhost:8000/api/health
# Check logs for "Auth: firebase" or "Auth: azure_ad"
```

### Database Connection Errors
```bash
# GCP: Ensure Cloud Run has Firestore access
gcloud run services add-iam-policy-binding ecosurvey-chat \
  --member=serviceAccount@...iam.gserviceaccount.com \
  --role=roles/datastore.user

# Azure: Check CosmosDB firewall allows Container Apps
# Private: Test DATABASE_URL connects from pod
```

## 📝 Version History

- **v2.0.0** (Current): Multi-cloud adapter pattern, observability, feature flags
- **v1.2.0**: Pinecone-only RAG with Firebase auth
- **v1.0.0**: Initial release

## 🤝 Contributing

1. Create feature branch: `git checkout -b feature/my-feature`
2. Test with all deployment targets: `DEPLOYMENT_TARGET=gcp|azure|private`
3. Run tests: `pytest`
4. Submit PR

## 📄 License

MIT License - See LICENSE file

## 🆘 Support

- **Docs**: See `docs/` folder for detailed guides
- **Issues**: Open GitHub issue
- **Deploy Help**: See `DEPLOYMENT_CHECKLIST.md`

---

**Made with ❤️ for evidence-grounded policy analysis**
