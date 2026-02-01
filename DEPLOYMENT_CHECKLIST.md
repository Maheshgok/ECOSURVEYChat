# Production Deployment Checklist

## Phase 1: Supabase Database Setup

### Get Supabase Connection String
- [ ] Log into Supabase Dashboard
- [ ] Go to **Settings → Database → Connection string**
- [ ] Select **URI** format
- [ ] Copy the connection string (format: `postgresql://postgres.[ID]:[PASSWORD]@db.[ID].supabase.co:5432/postgres`)

### Run Migrations
```bash
# Navigate to project root
cd c:\Users\Dell 5330\OneDrive\Documents\ECOSURVEYCHat

# Run migration helper (Windows PowerShell)
python run_supabase_migrations.py "postgresql://postgres.[ID]:[PASSWORD]@db.[ID].supabase.co:5432/postgres"

# Or manually run each migration via Supabase SQL Editor:
# https://app.supabase.com/project/[PROJECT_ID]/sql/new
```

- [ ] Migrations completed successfully
- [ ] pgvector extension enabled

### Verify Database
```bash
# Test connection
psql "postgresql://postgres.[ID]:[PASSWORD]@db.[ID].supabase.co:5432/postgres" -c "\dt"
```

- [ ] Connection successful
- [ ] Tables created (conversations, chunks, etc.)

---

## Phase 2: Backend Configuration

### Update Backend Environment
```bash
# Edit backend/.env.prod with:
DATABASE_URL=postgresql://postgres.[ID]:[PASSWORD]@db.[ID].supabase.co:5432/postgres
OPENAI_API_KEY=sk-...
FIREBASE_CREDENTIALS_JSON={...}
GCP_PROJECT_ID=watch-mail-trial
FRONTEND_URL=https://ecosurvey2026.netlify.app
CORS_ORIGINS=https://ecosurvey2026.netlify.app,https://your-cloud-run-url.run.app
```

- [ ] All environment variables set
- [ ] Secrets are NOT committed to Git

### Test Backend Locally
```bash
cd backend

# Test with Supabase (optional, for validation)
set DATABASE_URL=postgresql://...
python -m uvicorn app.main:app --reload --port 8000
```

- [ ] Local server starts without errors
- [ ] Can access http://localhost:8000/docs

---

## Phase 3: Docker Build & Push

### Build Docker Image
```bash
cd backend
docker build -t ecosurvey-backend:latest .
```

- [ ] Docker image builds successfully
- [ ] No build errors

### Optional: Test Locally
```bash
docker run -p 8000:8000 \
  -e DATABASE_URL=postgresql://... \
  -e OPENAI_API_KEY=sk-... \
  ecosurvey-backend:latest
```

- [ ] Container starts successfully
- [ ] Health check passes: http://localhost:8000/health

---

## Phase 4: Cloud Run Deployment

### Authenticate with GCP
```bash
gcloud auth login
gcloud config set project watch-mail-trial
```

- [ ] Authenticated with correct GCP project

### Option A: Deploy from Source (Recommended)
```bash
gcloud run deploy ecosurvey-backend \
  --source . \
  --platform managed \
  --region us-central1 \
  --memory 1Gi \
  --cpu 1 \
  --allow-unauthenticated
```

- [ ] Deployment started
- [ ] Waiting for build...
- [ ] Service deployed successfully

### Option B: Deploy from Docker (if you pushed to registry)
```bash
gcloud run deploy ecosurvey-backend \
  --image us-central1-docker.pkg.dev/watch-mail-trial/ecosurvey/backend:latest \
  --platform managed \
  --region us-central1 \
  --memory 1Gi \
  --cpu 1 \
  --allow-unauthenticated
```

### Set Environment Variables in Cloud Run
```bash
gcloud run services update ecosurvey-backend \
  --region us-central1 \
  --set-env-vars="DEBUG=False,ENVIRONMENT=production,GCP_PROJECT_ID=watch-mail-trial"
```

- [ ] Environment variables configured

### Set Secrets
```bash
# Use Cloud Secret Manager (recommended for sensitive data)
echo -n "postgresql://..." | gcloud secrets create supabase-db-url --data-file=-
echo -n "sk-..." | gcloud secrets create openai-key --data-file=-

# Update Cloud Run to use secrets
gcloud run services update ecosurvey-backend \
  --set-secrets="DATABASE_URL=supabase-db-url:latest,OPENAI_API_KEY=openai-key:latest"
```

- [ ] Secrets created in Cloud Secret Manager
- [ ] Service updated to use secrets

---

## Phase 5: Verify Cloud Run Deployment

### Get Service URL
```bash
gcloud run services describe ecosurvey-backend --region us-central1 --format='value(status.url)'
```

- [ ] Cloud Run URL obtained: `https://ecosurvey-backend-xxxxx.run.app`

### Test Health Endpoint
```bash
curl https://ecosurvey-backend-xxxxx.run.app/health
```

- [ ] Response: `{"status":"ok"}`

### Test API Documentation
```bash
# Visit in browser or curl
curl https://ecosurvey-backend-xxxxx.run.app/docs
```

- [ ] Swagger UI loads successfully

### Check Logs
```bash
gcloud run services logs read ecosurvey-backend --region us-central1 --limit 50
```

- [ ] No error logs
- [ ] Database connection successful

---

## Phase 6: Frontend Update

### Update Frontend API URL
```javascript
// File: frontend/src/pages/Chat.tsx
// Find and update:
const API_BASE_URL = "https://ecosurvey-backend-xxxxx.run.app";
```

- [ ] API URL updated

### Update CORS in Backend
```bash
# Make sure CORS_ORIGINS includes your Netlify frontend
CORS_ORIGINS=https://ecosurvey2026.netlify.app,https://ecosurvey-backend-xxxxx.run.app
```

- [ ] CORS configured correctly

### Test Frontend Connection
1. Visit https://ecosurvey2026.netlify.app
2. Sign in with Google/Firebase
3. Send test message in chat
4. Verify response received

- [ ] Frontend connects successfully
- [ ] Chat messages working
- [ ] No CORS errors in browser console

---

## Phase 7: Monitoring & Maintenance

### Set Up Cloud Run Alerts
```bash
# Via GCP Console: Cloud Run → Select service → Metrics
# Monitor: Error rate, Response time, Request count
```

- [ ] Alerts configured for errors

### View Logs
```bash
# Tail live logs
gcloud run services logs read ecosurvey-backend --region us-central1 --follow
```

- [ ] Can view real-time logs

### Scaling Configuration
```bash
# Update if needed
gcloud run services update ecosurvey-backend \
  --min-instances 1 \
  --max-instances 10 \
  --region us-central1
```

- [ ] Scaling configured

---

## Phase 8: Data Ingestion

Once deployment is complete:

1. [ ] Upload Economic Survey PDFs to Supabase Storage
2. [ ] Run chunking service on documents
3. [ ] Generate embeddings via OpenAI
4. [ ] Store vectors in Supabase pgvector table
5. [ ] Test retrieval with chat queries

---

## Cost Summary (Monthly Estimate)

| Service | Cost |
|---------|------|
| Supabase (Pro tier) | $25 |
| Cloud Run | $5-10 |
| OpenAI (embeddings + chat) | $10-30 |
| **Total** | **$40-65** |

---

## Rollback Plan

If issues occur:

```bash
# Scale down to 0 (pause service)
gcloud run services update ecosurvey-backend \
  --min-instances 0 \
  --region us-central1

# Or delete service to stop charges
gcloud run services delete ecosurvey-backend --region us-central1

# Frontend will still work with local backend
```

---

## Next Steps

After deployment:
1. Upload PDF documents
2. Generate embeddings
3. Run integration tests
4. Monitor performance
5. Optimize based on usage patterns
6. Phase 8: Add analytics features
