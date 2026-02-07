# GraphRAG Deployment Guide

## What is GraphRAG?

**GraphRAG** is an enhanced version of the RAG chatbot that uses **structured facts** instead of raw text chunks. This provides:

- ✅ **Explainable reasoning** - See exactly which facts support each answer
- ✅ **Higher precision** - Facts are extracted and verified, reducing hallucinations
- ✅ **Graph traversal** - Multi-hop reasoning by following fact relationships
- ✅ **Quantitative queries** - Native support for numerical comparisons
- ✅ **Temporal awareness** - Distinguish between historical, current, and projected data
- ✅ **Certainty scoring** - Know confidence levels for each fact

## Architecture Differences

### Standard RAG (edgechurn.ai)
```
User Query → Vector Search → Raw Chunks → LLM → Answer
```

### GraphRAG (research.edgechurn.ai)
```
User Query → Vector Search → Structured Facts → Graph Traversal → Reasoning Chain → Answer
```

## Fact Structure

Each fact is an atomic knowledge unit:

```json
{
  "fact_id": "f123...",
  "subject": "Fiscal Deficit",
  "predicate": "Targeted at",
  "value_quantity": 4.5,
  "value_unit": "%",
  "temporal_context": "FY2025-26",
  "certainty_score": 0.8,
  "sentiment_magnitude": -0.3,
  "verbatim_extraction": "The fiscal deficit is targeted at 4.5% of GDP...",
  "related_entities": ["Fiscal Policy", "GDP", "Budget 2026"],
  "source_origin": "Economic_Survey",
  "page_reference": 42
}
```

## Deployment Steps

### 1. Create New Pinecone Index for Facts

```powershell
# Create separate index for structured facts
# Index name: ecosurvey-facts (vs ecosurvey-embeddings for standard RAG)

# You'll need to do this in Pinecone console or via API
# Dimensions: 3072 (text-embedding-3-large)
# Metric: cosine
# Cloud: AWS or GCP (asia-south1 for low latency)
```

### 2. Deploy Backend to New Cloud Run Service

```powershell
# Deploy GraphRAG backend as separate service
gcloud run deploy ecosurvey-graphrag `
  --source . `
  --region asia-south1 `
  --allow-unauthenticated `
  --set-env-vars "DEPLOYMENT_TARGET=gcp,PINECONE_API_KEY=$env:PINECONE_API_KEY,OPENAI_API_KEY=$env:OPENAI_API_KEY,PINECONE_INDEX_NAME=ecosurvey-facts,FIREBASE_PROJECT_ID=watch-mail-trial,LOG_LEVEL=INFO" `
  --max-instances 20 `
  --memory 2Gi `
  --cpu 2 `
  --timeout 300
```

### 3. Create Subdomain (research.edgechurn.ai)

```powershell
# Map subdomain to GraphRAG service
gcloud run domain-mappings create `
  --service ecosurvey-graphrag `
  --domain research.edgechurn.ai `
  --region asia-south1 `
  --project watch-mail-trial

# Add DNS record in your domain provider:
# Name: research
# Type: CNAME
# Value: ghs.googlehosted.com
# TTL: 300
```

### 4. Update Frontend for GraphRAG

Create a new frontend build pointing to GraphRAG backend:

```javascript
// frontend/.env.graphrag
VITE_FIREBASE_API_KEY=AIzaSyDrr7F0k6r8WqApODpAdrvdgocTBMv0Ycw
VITE_FIREBASE_AUTH_DOMAIN=edgechurn.ai
VITE_FIREBASE_PROJECT_ID=watch-mail-trial
VITE_API_MODE=graphrag
VITE_BACKEND_URL=https://research.edgechurn.ai
```

```powershell
# Build frontend with GraphRAG config
cd frontend
npm run build -- --mode graphrag

# Deploy to Firebase Hosting (separate site)
firebase hosting:sites:create ecosurvey-graphrag
firebase target:apply hosting graphrag ecosurvey-graphrag
firebase deploy --only hosting:graphrag
```

### 5. Ingest Documents as Facts

```python
# scripts/ingest_facts.py
from app.services.fact_extractor import FactExtractor
from app.services.graphrag_retriever import GraphRAGRetriever
from pinecone import Pinecone
import fitz  # PyMuPDF

def ingest_document_as_facts(pdf_path: str, source_origin: str):
    extractor = FactExtractor()
    pc = Pinecone(api_key=os.getenv('PINECONE_API_KEY'))
    index = pc.Index("ecosurvey-facts")
    
    # Extract text from PDF
    doc = fitz.open(pdf_path)
    chunks = []
    for page_num, page in enumerate(doc, 1):
        text = page.get_text()
        if text.strip():
            chunks.append({
                'text': text,
                'page': page_num,
                'document_id': os.path.basename(pdf_path)
            })
    
    # Extract facts
    all_facts = extractor.batch_extract(chunks, source_origin)
    
    # Upload to Pinecone
    vectors = []
    for fact in all_facts:
        # Generate embedding for fact
        fact_text = f"{fact.subject} {fact.predicate} {fact.value_quantity or ''} {fact.value_unit or ''}"
        embedding = extractor.client.embeddings.create(
            input=fact_text,
            model="text-embedding-3-large"
        ).data[0].embedding
        
        # Prepare for upsert
        vectors.append({
            'id': fact.fact_id,
            'values': embedding,
            'metadata': fact.dict()
        })
    
    # Batch upsert
    index.upsert(vectors=vectors, batch_size=100)
    print(f"Ingested {len(all_facts)} facts from {pdf_path}")

# Run ingestion
if __name__ == "__main__":
    ingest_document_as_facts(
        "Economic_Survey_2026.pdf",
        "Economic_Survey"
    )
```

### 6. Update Firebase Hosting Config

```json
{
  "hosting": [
    {
      "target": "main",
      "public": "frontend/dist",
      "rewrites": [
        {
          "source": "/chatbot/ecosurveybudget2026/api/**",
          "run": {
            "serviceId": "ecosurvey-backend",
            "region": "asia-south1"
          }
        }
      ]
    },
    {
      "target": "graphrag",
      "public": "frontend/dist-graphrag",
      "rewrites": [
        {
          "source": "/api/**",
          "run": {
            "serviceId": "ecosurvey-graphrag",
            "region": "asia-south1"
          }
        }
      ]
    }
  ]
}
```

## Testing GraphRAG

### Test Fact Extraction
```powershell
curl -X POST https://research.edgechurn.ai/api/graphrag/extract-facts `
  -H "Content-Type: application/json" `
  -H "Authorization: Bearer $TOKEN" `
  -d '{
    "text": "The fiscal deficit is targeted at 4.5% of GDP for FY2025-26",
    "source_origin": "Economic_Survey",
    "page_reference": 42
  }'
```

### Test GraphRAG Query
```powershell
curl -X POST https://research.edgechurn.ai/api/graphrag/query `
  -H "Content-Type: application/json" `
  -H "Authorization: Bearer $TOKEN" `
  -d '{
    "question": "What is the fiscal deficit target for FY2025-26?",
    "top_k": 5,
    "use_graph_traversal": true
  }'
```

### Test Fact Search
```powershell
curl -X POST https://research.edgechurn.ai/api/graphrag/search-facts `
  -H "Content-Type: application/json" `
  -H "Authorization: Bearer $TOKEN" `
  -d '{
    "query_text": "GDP growth",
    "source_filter": ["Economic_Survey"],
    "min_certainty": 0.8,
    "top_k": 10
  }'
```

## Benefits Over Standard RAG

| Feature | Standard RAG | GraphRAG |
|---------|-------------|----------|
| **Answer Quality** | Good | Excellent (cited facts) |
| **Explainability** | Limited | Full reasoning chain |
| **Numerical Queries** | Struggles | Native support |
| **Multi-hop Reasoning** | None | Graph traversal |
| **Hallucination Risk** | Moderate | Low (fact-anchored) |
| **Latency** | ~1-2s | ~2-4s (graph traversal) |
| **Cost per Query** | $0.001 | $0.003 (fact extraction) |
| **Setup Complexity** | Low | Moderate |

## Use Cases for GraphRAG

**Best for:**
- ✅ Research queries requiring citations
- ✅ Quantitative comparisons (e.g., "How did deficit change from FY24 to FY25?")
- ✅ Multi-hop questions (e.g., "What caused the GDP slowdown, and what measures were taken?")
- ✅ Temporal analysis (trends over time)
- ✅ Compliance/audit scenarios (need exact sources)

**Use Standard RAG for:**
- ✅ Casual chat
- ✅ Broad exploratory questions
- ✅ Real-time conversational flow
- ✅ Lower latency requirements

## Monitoring

```powershell
# Check GraphRAG service status
gcloud run services describe ecosurvey-graphrag --region asia-south1

# View logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=ecosurvey-graphrag" --limit 50

# Check Pinecone index stats
curl -X GET https://research.edgechurn.ai/api/graphrag/stats `
  -H "Authorization: Bearer $TOKEN"
```

## Migration Path

1. **Phase 1 (Current)**: Run both systems in parallel (edgechurn.ai + research.edgechurn.ai)
2. **Phase 2**: Ingest all documents as facts (1-2 weeks for full corpus)
3. **Phase 3**: A/B test answer quality
4. **Phase 4**: Decide on primary system or keep both for different use cases

## Cost Comparison

**Standard RAG:**
- Embedding: $0.00013 per 1K tokens
- LLM response: $0.006 per 1K tokens
- **Per query: ~$0.001**

**GraphRAG:**
- Fact extraction (one-time): $0.002 per page
- Embedding (facts): $0.00013 per 1K tokens
- LLM reasoning: $0.006 per 1K tokens
- **Per query: ~$0.003**
- **Ingestion cost: ~$200 for 100K pages (one-time)**

---

Ready to deploy? Run:
```powershell
# 1. Create Pinecone index
# 2. Deploy backend
gcloud run deploy ecosurvey-graphrag --source .

# 3. Run fact ingestion
python scripts/ingest_facts.py

# 4. Test
curl https://research.edgechurn.ai/api/graphrag/stats
```
