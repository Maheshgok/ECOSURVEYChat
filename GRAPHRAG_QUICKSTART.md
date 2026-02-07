# GraphRAG Quick Start Guide

## 🚀 Deploy GraphRAG Backend

### Prerequisites
1. ✅ GCP project configured (watch-mail-trial)
2. ✅ Pinecone account with API key
3. ✅ OpenAI API key
4. ✅ gcloud CLI installed and authenticated

### Step 1: Set Environment Variables

```powershell
$env:PINECONE_API_KEY = "your-pinecone-api-key"
$env:OPENAI_API_KEY = "your-openai-api-key"
$env:FIREBASE_PROJECT_ID = "watch-mail-trial"
```

### Step 2: Create Pinecone Index

**Option A: Via Pinecone Console**
1. Go to https://app.pinecone.io
2. Create new index with:
   - Name: `ecosurvey-facts`
   - Dimensions: `3072`
   - Metric: `cosine`
   - Cloud: `AWS` or `GCP`
   - Region: `us-east-1` (or closest to your region)

**Option B: Via Python**

```python
from pinecone import Pinecone, ServerlessSpec
import os

pc = Pinecone(api_key=os.getenv('PINECONE_API_KEY'))

pc.create_index(
    name='ecosurvey-facts',
    dimension=3072,
    metric='cosine',
    spec=ServerlessSpec(cloud='aws', region='us-east-1')
)
```

### Step 3: Deploy GraphRAG Backend

```powershell
# Deploy to Cloud Run
.\deploy_graphrag.ps1
```

This will:
- Build Docker image with `Dockerfile.graphrag`
- Deploy to Cloud Run service `ecosurvey-graphrag`
- Set up with 2GB memory, 2 CPUs
- Configure environment variables
- Output service URL

**Expected output:**
```
Service URL: https://ecosurvey-graphrag-812016027146.asia-south1.run.app
Health Check: https://ecosurvey-graphrag-812016027146.asia-south1.run.app/api/health
```

### Step 4: Test Deployment

```powershell
# Test health endpoint
$backend_url = "https://ecosurvey-graphrag-812016027146.asia-south1.run.app"
Invoke-RestMethod -Uri "$backend_url/api/health" -Method Get

# Should return:
# {
#   "status": "healthy",
#   "service": "graphrag",
#   "version": "1.0.0",
#   "pinecone_index": "ecosurvey-facts"
# }
```

---

## 📊 Ingest Documents as Facts

### Step 5: Install Dependencies

```powershell
cd backend
pip install -r requirements.txt
pip install PyMuPDF  # For PDF parsing
```

### Step 6: Run Fact Ingestion

```powershell
# Ingest Economic Survey PDF
python scripts/ingest_facts.py "path/to/Economic_Survey_2026.pdf" --source "Economic_Survey" --create-index

# Or if index already exists:
python scripts/ingest_facts.py "path/to/Economic_Survey_2026.pdf" --source "Economic_Survey"
```

**Example output:**
```
INFO - Extracting facts from 250 chunks...
INFO - Extracted 1,247 facts
INFO - Upserting 1,247 vectors to Pinecone...
INFO - Upserted batch 125/125
==================================================
INGESTION COMPLETE
Document: Economic_Survey_2026.pdf
Chunks processed: 250
Facts extracted: 1,247
Facts per chunk: 4.99
Elapsed time: 342.5s
Throughput: 3.64 facts/s
==================================================
Total facts in index: 1,247
Index fullness: 0.12%
```

**What gets extracted:**

From: *"The fiscal deficit is targeted at 4.5% of GDP for FY2025-26, down from 4.9% in FY2024-25."*

To:
```json
[
  {
    "subject": "Fiscal Deficit",
    "predicate": "Targeted at",
    "value_quantity": 4.5,
    "value_unit": "%",
    "temporal_context": "FY2025-26",
    "certainty_score": 0.95,
    "sentiment_magnitude": 0.0,
    "related_entities": ["Fiscal Policy", "GDP", "Budget"]
  },
  {
    "subject": "Fiscal Deficit",
    "predicate": "Was",
    "value_quantity": 4.9,
    "value_unit": "%",
    "temporal_context": "FY2024-25",
    "certainty_score": 1.0,
    "sentiment_magnitude": 0.0,
    "related_entities": ["Fiscal Policy", "GDP"]
  }
]
```

---

## 🔗 Set Up Subdomain (research.edgechurn.ai)

### Step 7: Create Domain Mapping

```powershell
# Map research.edgechurn.ai to GraphRAG service
gcloud run domain-mappings create `
  --service ecosurvey-graphrag `
  --domain research.edgechurn.ai `
  --region asia-south1 `
  --project watch-mail-trial
```

### Step 8: Update DNS

In your domain registrar (where edgechurn.ai is registered):

1. Add CNAME record:
   - **Name:** `research`
   - **Type:** `CNAME`
   - **Value:** `ghs.googlehosted.com`
   - **TTL:** `300`

2. Wait 5-15 minutes for DNS propagation

3. Verify:
```powershell
nslookup research.edgechurn.ai
# Should resolve to ghs.googlehosted.com
```

---

## 🧪 Test GraphRAG API

### Test Fact Extraction

```powershell
# Get Firebase auth token first
$token = "your-firebase-id-token"

# Extract facts from sample text
$body = @{
    text = "The fiscal deficit is targeted at 4.5% of GDP for FY2025-26"
    source_origin = "Economic_Survey"
    page_reference = 42
} | ConvertTo-Json

Invoke-RestMethod -Uri "https://research.edgechurn.ai/api/graphrag/extract-facts" `
    -Method Post `
    -Headers @{"Authorization" = "Bearer $token"; "Content-Type" = "application/json"} `
    -Body $body
```

### Test GraphRAG Query

```powershell
# Ask a question with reasoning
$body = @{
    question = "What is the fiscal deficit target for FY2025-26?"
    top_k = 5
    use_graph_traversal = $true
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri "https://research.edgechurn.ai/api/graphrag/query" `
    -Method Post `
    -Headers @{"Authorization" = "Bearer $token"; "Content-Type" = "application/json"} `
    -Body $body

Write-Host "Answer: $($response.answer)" -ForegroundColor Green
Write-Host "Reasoning:" -ForegroundColor Yellow
$response.reasoning_steps | ForEach-Object { Write-Host "  - $_" -ForegroundColor Cyan }
```

**Expected response:**
```json
{
  "answer": "The fiscal deficit is targeted at 4.5% of GDP for FY2025-26.",
  "reasoning_steps": [
    "Retrieved 3 facts about fiscal deficit",
    "Found direct statement with certainty 0.95",
    "Verified against historical data (FY2024-25: 4.9%)",
    "Confirmed downward trend"
  ],
  "supporting_facts": [
    {
      "subject": "Fiscal Deficit",
      "predicate": "Targeted at",
      "value_quantity": 4.5,
      "certainty_score": 0.95,
      "source_origin": "Economic_Survey",
      "page_reference": 42
    }
  ],
  "confidence": 0.95
}
```

### Test Fact Search

```powershell
# Search for GDP-related facts
$body = @{
    query_text = "GDP growth"
    source_filter = @("Economic_Survey")
    min_certainty = 0.8
    top_k = 10
} | ConvertTo-Json

Invoke-RestMethod -Uri "https://research.edgechurn.ai/api/graphrag/search-facts" `
    -Method Post `
    -Headers @{"Authorization" = "Bearer $token"; "Content-Type" = "application/json"} `
    -Body $body
```

### Get Index Stats

```powershell
Invoke-RestMethod -Uri "https://research.edgechurn.ai/api/graphrag/stats" `
    -Headers @{"Authorization" = "Bearer $token"}

# Returns:
# {
#   "total_facts": 1247,
#   "index_fullness": 0.12,
#   "dimensions": 3072
# }
```

---

## 🎨 Update Frontend (Optional)

### Option 1: Add GraphRAG Toggle to Existing Frontend

Update [Chat.jsx](frontend/src/components/Chat.jsx):

```javascript
const [useGraphRAG, setUseGraphRAG] = useState(false);

const sendMessage = async () => {
  const endpoint = useGraphRAG 
    ? '/api/graphrag/query'
    : '/chatbot/ecosurveybudget2026/api/rag-chat-v2';
  
  // ... rest of logic
};

// Add toggle in render:
<label>
  <input type="checkbox" checked={useGraphRAG} onChange={e => setUseGraphRAG(e.target.checked)} />
  Use GraphRAG (with reasoning)
</label>
```

### Option 2: Create Separate Frontend Build

```powershell
# Create separate env file
Copy-Item frontend/.env frontend/.env.graphrag
# Edit: VITE_BACKEND_URL=https://research.edgechurn.ai

# Build with GraphRAG config
cd frontend
npm run build -- --mode graphrag

# Deploy to separate Firebase site
firebase hosting:sites:create ecosurvey-graphrag
firebase target:apply hosting graphrag ecosurvey-graphrag
firebase deploy --only hosting:graphrag
```

---

## 📈 Monitoring

### Check Service Health

```powershell
# Cloud Run logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=ecosurvey-graphrag" --limit 50

# Service status
gcloud run services describe ecosurvey-graphrag --region asia-south1

# Index statistics
Invoke-RestMethod -Uri "https://research.edgechurn.ai/api/graphrag/stats" -Headers @{"Authorization" = "Bearer $token"}
```

### Cost Estimate

**One-time ingestion:**
- 100 pages × 5 facts/page = 500 facts
- Fact extraction: 500 facts × $0.002 = $1.00
- Embeddings: 500 × $0.00013 = $0.065
- **Total: ~$1.07 per 100 pages**

**Per query:**
- Vector search: Free (Pinecone starter)
- LLM reasoning: ~$0.003
- **Total: ~$0.003 per query**

---

## 🎯 Comparison: Standard RAG vs GraphRAG

| Query | Standard RAG | GraphRAG |
|-------|-------------|----------|
| "What is the fiscal deficit target?" | "The fiscal deficit target is 4.5%" | "4.5% for FY2025-26 (certainty: 0.95)<br>Source: Economic Survey p.42<br>Context: Down from 4.9% in FY2024-25" |
| "How did GDP change over time?" | *Lists various mentions* | *Structured timeline with quantified changes and trends* |
| "Why did inflation rise?" | *May hallucinate connections* | *Explicit fact chain: supply shock → price increase → CPI rise* |

---

## ✅ Checklist

- [ ] Pinecone index `ecosurvey-facts` created
- [ ] GraphRAG backend deployed to Cloud Run
- [ ] Health check passes (`/api/health`)
- [ ] PDF documents ingested as facts
- [ ] Subdomain `research.edgechurn.ai` mapped
- [ ] DNS CNAME record added
- [ ] Frontend updated (or toggle added)
- [ ] Test queries return structured answers
- [ ] Firebase authorized domain includes `edgechurn.ai`

---

## 🆘 Troubleshooting

### "Index not found" error
```powershell
# Verify index exists
python -c "from pinecone import Pinecone; import os; pc = Pinecone(api_key=os.getenv('PINECONE_API_KEY')); print([idx.name for idx in pc.list_indexes()])"
```

### Slow fact extraction
- Reduce batch size: `python scripts/ingest_facts.py <pdf> --batch-size 5`
- Use faster OpenAI model (but lower quality): Edit `fact_extractor.py` → change to `gpt-3.5-turbo`

### Frontend can't reach backend
1. Check CORS origins in `main_graphrag.py`
2. Verify Firebase rewrite rules in `firebase.json`
3. Check domain mapping: `gcloud run domain-mappings describe research.edgechurn.ai`

### High costs
- Use Pinecone Starter (free tier: 100K vectors)
- Cache embeddings in ingestion script
- Set `max_instances=5` in Cloud Run deploy

---

Ready to deploy? Run:

```powershell
.\deploy_graphrag.ps1
```

Then ingest your first document!
