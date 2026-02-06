# Multi-Cloud Deployment Guide

## Overview
This guide explains how to deploy the Economic Survey Chat RAG system to different cloud providers with minimal configuration changes.

## Core Concept: Adapter Pattern

The system uses **adapters** to abstract cloud-specific services:

- **Auth Adapter**: Firebase → Azure AD → Custom JWT
- **Session Adapter**: Firestore → CosmosDB → Postgres → Redis
- **Vector Adapter**: Pinecone → Azure AI Search

**Switch clouds by changing ONE environment variable:**
```bash
DEPLOYMENT_TARGET=gcp    # Firebase + Firestore
DEPLOYMENT_TARGET=azure  # Azure AD + CosmosDB
DEPLOYMENT_TARGET=private # JWT + Postgres
```

## Deployment Workflows

### 🔵 GCP Cloud Run (Recommended for Quick Start)

**Advantages:**
- Zero config (uses default service account)
- Auto-scales to zero
- Firebase auth built-in

**Steps:**
```bash
# 1. Install Google Cloud SDK
curl https://sdk.cloud.google.com | bash

# 2. Login and set project
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# 3. Set minimum environment variables
cat > .env <<EOF
PINECONE_API_KEY=pk-...
OPENAI_API_KEY=sk-...
DEPLOYMENT_TARGET=gcp
EOF

# 4. Deploy (builds and deploys in one command)
gcloud run deploy ecosurvey-chat \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars-file .env

# 5. Get URL
gcloud run services describe ecosurvey-chat --format='value(status.url)'
```

**Frontend Setup:**
```bash
cd frontend
npm install

# Set backend URL in .env.production
echo "VITE_API_URL=https://YOUR-CLOUD-RUN-URL" > .env.production

# Deploy to Firebase Hosting
firebase deploy --only hosting
```

**Cost:** ~$0-5/month (Cloud Run free tier: 2M requests/month)

---

### 🔷 Azure Container Apps

**Advantages:**
- Native Microsoft SSO (Azure AD)
- Cosmos DB global distribution
- Application Insights monitoring

**Prerequisites:**
1. Azure subscription
2. Azure AD app registration
3. CosmosDB account (NoSQL API)

**Steps:**
```bash
# 1. Install Azure CLI
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# 2. Login
az login

# 3. Create resource group
az group create --name ecosurvey-rg --location eastus

# 4. Create CosmosDB account (takes ~5 minutes)
az cosmosdb create \
  --name ecosurvey-cosmos \
  --resource-group ecosurvey-rg \
  --kind GlobalDocumentDB \
  --default-consistency-level Session

# 5. Get CosmosDB connection info
COSMOS_KEY=$(az cosmosdb keys list \
  --name ecosurvey-cosmos \
  --resource-group ecosurvey-rg \
  --query primaryMasterKey -o tsv)
COSMOS_ENDPOINT="https://ecosurvey-cosmos.documents.azure.com:443/"

# 6. Register Azure AD app (for SSO)
az ad app create \
  --display-name "Economic Survey Chat" \
  --sign-in-audience AzureADMyOrg
# Copy Application (client) ID and Tenant ID

# 7. Set environment variables
cat > .env <<EOF
DEPLOYMENT_TARGET=azure
AZURE_TENANT_ID=YOUR_TENANT_ID
AZURE_CLIENT_ID=YOUR_CLIENT_ID
COSMOS_DB_ENDPOINT=$COSMOS_ENDPOINT
COSMOS_DB_KEY=$COSMOS_KEY
COSMOS_DB_DATABASE=ecosurvey-chat
COSMOS_DB_CONTAINER=sessions
PINECONE_API_KEY=pk-...
OPENAI_API_KEY=sk-...
EOF

# 8. Deploy Container App
az containerapp up \
  --name ecosurvey-chat \
  --resource-group ecosurvey-rg \
  --location eastus \
  --environment-variables-file .env \
  --source . \
  --target-port 8000 \
  --ingress external

# 9. Get URL
az containerapp show \
  --name ecosurvey-chat \
  --resource-group ecosurvey-rg \
  --query properties.configuration.ingress.fqdn -o tsv
```

**Frontend Setup (Azure Static Web Apps):**
```bash
cd frontend

# Set backend URL
echo "VITE_API_URL=https://YOUR-CONTAINER-APP-URL" > .env.production

# Deploy
az staticwebapp create \
  --name ecosurvey-frontend \
  --resource-group ecosurvey-rg \
  --source ./
```

**Cost:** ~$15-30/month (Container Apps Basic tier, CosmosDB provisioned throughput)

---

### ⚫ Private Cloud / Kubernetes

**Advantages:**
- Full control & data privacy
- Custom JWT auth (integrate with existing SSO)
- Postgres + Redis for performance

**Prerequisites:**
1. Kubernetes cluster (1.25+) or Docker Compose
2. PostgreSQL 15+
3. Redis 7+ (optional)

**Docker Compose Quickstart:**
```bash
# 1. Copy docker-compose.yml to your server
wget https://raw.githubusercontent.com/YOUR-REPO/.../docker-compose.yml

# 2. Generate JWT secret
JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")

# 3. Edit docker-compose.yml environment section
vim docker-compose.yml
# Set PINECONE_API_KEY, OPENAI_API_KEY, JWT_SECRET_KEY=$JWT_SECRET

# 4. Start services
docker-compose up -d

# 5. Run database migrations
docker-compose exec backend python -m alembic upgrade head

# 6. Check health
curl http://localhost:8000/api/health
```

**Kubernetes Deployment:**
```bash
# 1. Create namespace
kubectl create namespace ecosurvey

# 2. Create secrets
kubectl create secret generic ecosurvey-secrets \
  --from-literal=jwt-secret-key=$(openssl rand -base64 32) \
  --from-literal=openai-api-key=sk-... \
  --from-literal=pinecone-api-key=pk-... \
  --from-literal=database-url=postgresql://user:pass@postgres:5432/ecosurvey \
  -n ecosurvey

# 3. Create config map
kubectl create configmap ecosurvey-config \
  --from-literal=DEPLOYMENT_TARGET=private \
  --from-literal=LOG_LEVEL=INFO \
  -n ecosurvey

# 4. Deploy Postgres (if not using external DB)
kubectl apply -f k8s/postgres.yaml -n ecosurvey

# 5. Deploy Redis (optional, for caching)
kubectl apply -f k8s/redis.yaml -n ecosurvey

# 6. Deploy backend
kubectl apply -f k8s/backend-deployment.yaml -n ecosurvey
kubectl apply -f k8s/backend-service.yaml -n ecosurvey

# 7. Deploy ingress
kubectl apply -f k8s/ingress.yaml -n ecosurvey

# 8. Wait for rollout
kubectl rollout status deployment/ecosurvey-backend -n ecosurvey

# 9. Get external IP
kubectl get ingress -n ecosurvey
```

**Cost:** $100-500/month (depends on cluster size, bandwidth)

---

## Configuration Comparison

| Feature | GCP | Azure | Private |
|---------|-----|-------|---------|
| **Auth** | Firebase (free) | Azure AD (included) | Custom JWT |
| **Sessions** | Firestore (free tier) | CosmosDB ($24/mo+) | Postgres/Redis |
| **Vectors** | Pinecone ($70/mo) | Azure AI Search ($250/mo) or Pinecone | Pinecone |
| **Monitoring** | Cloud Logging (free tier) | App Insights ($2.3/GB) | Prometheus (self-host) |
| **Scaling** | Auto (0-1000 instances) | Auto (0-30 instances) | Manual (HPA) |
| **Cold Start** | ~1-3s | ~2-5s | None (always warm) |
| **Min Cost/mo** | $5 | $20 | $100 |
| **Best For** | Prototypes, startups | Enterprise, Microsoft shops | Regulated industries, on-prem |

## Testing Adapter Switching

**Verify adapters load correctly:**

```bash
# Test GCP mode
DEPLOYMENT_TARGET=gcp python -c "
from app.core.env_loader import get_deployment_config
config = get_deployment_config()
print(f'Auth: {config.auth.provider}')  # Should be 'firebase'
print(f'Sessions: {config.sessions.provider}')  # Should be 'firestore'
"

# Test Azure mode
DEPLOYMENT_TARGET=azure python -c "
from app.core.env_loader import get_deployment_config
config = get_deployment_config()
print(f'Auth: {config.auth.provider}')  # Should be 'azure_ad'
print(f'Sessions: {config.sessions.provider}')  # Should be 'cosmosdb'
"

# Test Private mode
DEPLOYMENT_TARGET=private python -c "
from app.core.env_loader import get_deployment_config
config = get_deployment_config()
print(f'Auth: {config.auth.provider}')  # Should be 'custom_jwt'
print(f'Sessions: {config.sessions.provider}')  # Should be 'redis' or 'postgres'
"
```

## Migration Between Clouds

**Scenario: Move from GCP to Azure**

1. **Export data from Firestore:**
```bash
gcloud firestore export gs://YOUR-BUCKET/firestore-backup
```

2. **Import to CosmosDB:**
```python
# scripts/migrate_firestore_to_cosmos.py
from google.cloud import firestore
from azure.cosmos import CosmosClient

# Read from Firestore, write to CosmosDB
# See scripts/ folder for full implementation
```

3. **Switch deployment target:**
```bash
# Update .env
DEPLOYMENT_TARGET=azure

# Test locally
python -m app.main

# Deploy to Azure
az containerapp up ...
```

4. **Update frontend auth:**
```javascript
// Change from:
import { getAuth } from 'firebase/auth';

// To:
import { PublicClientApplication } from '@azure/msal-browser';
```

## Rollback Procedure

If deployment fails:

```bash
# GCP
gcloud run services update ecosurvey-chat --tag rollback
gcloud run services update-traffic ecosurvey-chat --to-revisions PREVIOUS_REVISION=100

# Azure
az containerapp revision list --name ecosurvey-chat --resource-group ecosurvey-rg
az containerapp revision activate --name PREVIOUS_REVISION --resource-group ecosurvey-rg

# Kubernetes
kubectl rollout undo deployment/ecosurvey-backend -n ecosurvey
```

## Monitoring & Alerts

**GCP:**
```bash
# View logs
gcloud run services logs read ecosurvey-chat --limit 50

# Set up alerts (CPU > 80%)
gcloud alpha monitoring policies create --config=alerts/cpu-alert.yaml
```

**Azure:**
```bash
# View logs
az containerapp logs show --name ecosurvey-chat --resource-group ecosurvey-rg

# Set up alerts
az monitor metrics alert create \
  --name high-cpu-alert \
  --resource ecosurvey-chat \
  --condition "avg requests > 1000"
```

**Kubernetes:**
```bash
# View logs
kubectl logs -f deployment/ecosurvey-backend -n ecosurvey

# Prometheus alerts (from k8s/prometheus-rules.yaml)
kubectl apply -f k8s/prometheus-rules.yaml
```

## Security Checklist

- [ ] Rotate API keys regularly (Pinecone, OpenAI)
- [ ] Enable Cloud Armor/ WAF (GCP/Azure)
- [ ] Set up VPC/Private Endpoints (database access)
- [ ] Enable audit logging
- [ ] Scan container images (Snyk, Trivy)
- [ ] Use secrets management (GCP Secret Manager, Azure Key Vault, Kubernetes Secrets)
- [ ] Set resource quotas (prevent cost overruns)
- [ ] Enable HTTPS only
- [ ] Configure CORS properly

## Performance Tuning

**Cold Start Optimization:**
```yaml
# deployment.gcp.yaml
startup_probe:
  initial_delay_seconds: 0
  timeout_seconds: 240
  
min_instances: 1  # Keep 1 instance warm (costs ~$8/mo)
```

**Connection Pooling:**
```python
# For Postgres adapter
POSTGRES_POOL_SIZE=20
POSTGRES_MAX_OVERFLOW=10
```

**Caching:**
```bash
# Enable Redis cache
FEATURE_REDIS_CACHE=true
REDIS_HOST=your-redis-host
```

## Support

- **Deployment Issues:** Open GitHub issue with `deployment` label
- **Cloud-Specific Questions:** See `docs/cloud-specific/` folder
- **Emergency Rollback:** Run `bash EMERGENCY_ROLLBACK.sh`

---

**Next Steps:** See [README_V2.md](README_V2.md) for feature flags, A/B testing, and observability guides.
