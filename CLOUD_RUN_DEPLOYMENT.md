# Cloud Run Deployment Guide

## Prerequisites
- GCP Project ID: `watch-mail-trial`
- Docker installed locally
- `gcloud` CLI installed and authenticated
- Supabase project created with URL and API keys

## Setup Steps

### 1. Configure Supabase Database

First, run migrations on your Supabase database:

```bash
# Get your Supabase connection string from:
# Supabase Dashboard → Settings → Database → Connection string (URI format)

# Option A: Using psql
psql "postgresql://postgres.[PROJECT_ID]:[PASSWORD]@db.[PROJECT_ID].supabase.co:5432/postgres" \
  -f backend/migrations/001_init_phase1.sql \
  -f backend/migrations/002_add_auth_tables.sql \
  -f backend/migrations/003_add_ingestion_tables.sql \
  -f backend/migrations/004_add_data_storage.sql \
  -f backend/migrations/005_add_insights.sql \
  -f backend/migrations/006_add_summaries.sql \
  -f backend/migrations/007_fix_conversations_schema.sql

# Option B: Using Supabase SQL Editor
# Copy each migration file contents and run in:
# Supabase Dashboard → SQL Editor → New query
```

### 2. Enable pgvector on Supabase

```bash
psql "postgresql://postgres.[PROJECT_ID]:[PASSWORD]@db.[PROJECT_ID].supabase.co:5432/postgres" \
  -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### 3. Build Docker Image

```bash
# From project root directory
cd backend

# Build locally (optional for testing)
docker build -t ecosurvey-backend:latest .

# Tag for GCP Artifact Registry
docker tag ecosurvey-backend:latest \
  us-central1-docker.pkg.dev/watch-mail-trial/ecosurvey/backend:latest
```

### 4. Deploy to Cloud Run

```bash
# Using gcloud CLI directly (simplest)
gcloud run deploy ecosurvey-backend \
  --source . \
  --platform managed \
  --region us-central1 \
  --project watch-mail-trial \
  --memory 1Gi \
  --cpu 1 \
  --timeout 3600 \
  --set-env-vars "DEBUG=False,ENVIRONMENT=production,GCP_PROJECT_ID=watch-mail-trial" \
  --set-secrets "DATABASE_URL=supabase-db-url:latest,OPENAI_API_KEY=openai-key:latest,FIREBASE_CREDENTIALS_JSON=firebase-creds:latest" \
  --allow-unauthenticated
```

### 5. Using Cloud Secret Manager

For sensitive data, use GCP Secret Manager:

```bash
# Create secrets
echo -n "postgresql://postgres.[ID]:[PASSWORD]@db.[ID].supabase.co:5432/postgres" | \
  gcloud secrets create supabase-db-url --data-file=-

echo -n "sk-..." | \
  gcloud secrets create openai-key --data-file=-

# Grant Cloud Run service account access
gcloud secrets add-iam-policy-binding supabase-db-url \
  --member=serviceAccount:PROJECT_ID-compute@developer.gserviceaccount.com \
  --role=roles/secretmanager.secretAccessor
```

### 6. Update Frontend API URL

After Cloud Run deployment, update your frontend to use the production backend URL:

```javascript
// frontend/src/pages/Chat.tsx
const API_BASE_URL = "https://ecosurvey-backend-xxxxx.run.app";  // Your Cloud Run URL
```

### 7. Test Deployment

```bash
# Get your Cloud Run URL
gcloud run services describe ecosurvey-backend --region us-central1 --project watch-mail-trial

# Test health endpoint
curl https://your-cloud-run-url.run.app/health

# Test API docs
curl https://your-cloud-run-url.run.app/docs
```

## Environment Variables Reference

| Variable | Source | Notes |
|----------|--------|-------|
| `DATABASE_URL` | Supabase Settings | Full PostgreSQL connection string |
| `OPENAI_API_KEY` | Your OpenAI account | Keep secret! Use Cloud Secret Manager |
| `FIREBASE_CREDENTIALS_JSON` | Firebase console | Service account JSON |
| `GCP_PROJECT_ID` | watch-mail-trial | For Analytics and other GCP services |
| `FRONTEND_URL` | https://ecosurvey2026.netlify.app | For CORS |
| `CORS_ORIGINS` | Frontend URLs | Comma-separated list |

## Monitoring & Logs

```bash
# Stream logs from Cloud Run
gcloud run services logs read ecosurvey-backend --region us-central1 --project watch-mail-trial

# View metrics and errors
# Go to: Cloud Console → Cloud Run → Select service → Metrics
```

## Cost Estimation

- **Cloud Run**: ~$5-10/mo (2 vCPU, 1GB RAM, minimal traffic)
- **Supabase**: $25/mo (Pro tier)
- **OpenAI**: $10-30/mo (depends on usage)
- **Total**: ~$40-65/mo

## Troubleshooting

### Database Connection Issues
```bash
# Test connection locally
psql "postgresql://..."  # From supabase URL

# Check Cloud Run service account has Secret Manager access
gcloud projects get-iam-policy watch-mail-trial
```

### API Not Responding
```bash
# Check Cloud Run logs
gcloud run services logs read ecosurvey-backend --limit 50

# Verify environment variables
gcloud run services describe ecosurvey-backend --format='value(status.template.spec.containers[0].env)'
```

### CORS Errors
- Make sure `CORS_ORIGINS` includes your Netlify frontend URL
- Update `FRONTEND_URL` and `FRONTEND_API_URL` in backend settings

## Next Steps

1. ✅ Run migrations on Supabase
2. ✅ Deploy backend to Cloud Run
3. ✅ Update frontend API URL
4. Upload PDF documents to Supabase Storage
5. Generate embeddings for documents
6. Test end-to-end chat flow
