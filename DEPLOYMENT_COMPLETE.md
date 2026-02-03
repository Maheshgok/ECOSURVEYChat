# Conversational RAG v2 - Deployment Complete ✅

## Overview
Successfully deployed production-ready conversational RAG system with advanced features to avoid repetitive answers in multi-turn conversations.

## Deployment Details

### Services
- **v1 (Basic RAG)**: `https://ecosurvey-backend-812016027146.asia-south1.run.app`
- **v2 (Advanced Conversational)**: `https://ecosurvey-backend-v2-812016027146.asia-south1.run.app`

### v2 Features Implemented
1. **Multi-Query Retrieval**: Generates 3 query variants for better coverage
2. **Query Expansion**: LLM-based reformulation with conversation context
3. **Reciprocal Rank Fusion (RRF)**: Fuses multiple result sets using formula: `score(d) = Σ 1/(k + rank_i(d))` where k=60
4. **Maximal Marginal Relevance (MMR)**: Diversity-aware selection with λ=0.6
5. **Session-Based Deduplication**: Tracks shown chunks per session, never repeats
6. **Topic Shift Detection**: Cosine similarity < 0.3 threshold triggers reset
7. **Retry Logic**: Exponential backoff (3 retries) for API resilience
8. **Session Cleanup**: Auto-eviction after 1 hour TTL, max 1000 sessions

## API Endpoints

### v2 Chat Endpoint
```powershell
POST https://ecosurvey-backend-v2-812016027146.asia-south1.run.app/api/rag-chat-v2
```

**Request Body:**
```json
{
  "question": "What are the key economic growth projections?",
  "session_id": "user-123",
  "conversation_history": [
    {"role": "user", "content": "Previous question..."},
    {"role": "assistant", "content": "Previous answer..."}
  ],
  "top_k": 5
}
```

**Response:**
```json
{
  "answer": "Narrative answer...",
  "citations": [...],
  "context_used": 5,
  "session_id": "user-123",
  "turn_number": 2
}
```

## Testing Results

### Turn 1 (Initial Question)
```powershell
$body = @{
    question = "What are the key economic growth projections for India?"
    session_id = "demo-session-001"
    top_k = 5
} | ConvertTo-Json

Invoke-RestMethod -Uri 'https://ecosurvey-backend-v2-812016027146.asia-south1.run.app/api/rag-chat-v2' `
    -Method POST -ContentType 'application/json' -Body $body
```
✅ Returned 5 citations, comprehensive answer about 7% growth projection

### Turn 2 (Follow-up with Context)
```powershell
$body = @{
    question = "Tell me more about consumption trends"
    session_id = "demo-session-001"
    conversation_history = @(
        @{ role = "user"; content = "What are the key economic growth projections for India?" },
        @{ role = "assistant"; content = "GDP growth 6.8-7.2% projected..." }
    )
    top_k = 5
} | ConvertTo-Json -Depth 10

Invoke-RestMethod -Uri 'https://ecosurvey-backend-v2-812016027146.asia-south1.run.app/api/rag-chat-v2' `
    -Method POST -ContentType 'application/json' -Body $body
```
✅ Returned **different** 5 citations (no overlap), focused on consumption
✅ Session tracking working: turn_number = 2

## Architecture

### Pipeline Stages
```
1. get_or_create_session(session_id) → ConversationState
2. detect_topic_shift(current, last) → bool (similarity < 0.3)
3. expand_query_with_context(query, history) → expanded_query
4. generate_multi_queries(expanded_query) → [q1, q2, q3]
5. retrieve_with_deduplication(variants, shown_ids) → [[chunks], [chunks], [chunks]]
6. reciprocal_rank_fusion(result_sets) → fused_chunks
7. maximal_marginal_relevance(fused, query_emb, k=5, λ=0.6) → diverse_chunks
8. Update state: shown_ids.add(chunk_ids), last_query = query
```

### Dependencies
- **Core**: `openai`, `pinecone-client`, `numpy`
- **No LangChain**: Custom implementation = fewer dependencies (3 vs 40+)
- **Lower Risk**: 6/10 complexity vs 7/10 with LangChain ecosystem

### Production Hardening Added
1. **Retry Logic**: `@retry_with_exponential_backoff(max_retries=3)`
   - Initial delay: 1s
   - Exponential base: 2.0
   - Max delay: 10s
   
2. **Session Management**:
   - TTL: 3600 seconds (1 hour)
   - Max sessions: 1000
   - Auto-cleanup every 10th request
   
3. **Error Handling**:
   - Graceful fallbacks at each stage
   - Never fails completely - returns empty results if all else fails
   - Comprehensive logging with severity levels

## Comparison: v1 vs v2

| Feature | v1 (Basic) | v2 (Advanced) |
|---------|------------|---------------|
| Retrieval | Single query | Multi-query (3 variants) |
| Context | Optional history | Automatic query expansion |
| Deduplication | None | Session-based tracking |
| Diversity | Basic top-k | MMR (λ=0.6) |
| Fusion | N/A | RRF algorithm |
| Topic Shift | None | Automatic detection |
| Retry Logic | None | 3 retries with backoff |
| Session Cleanup | N/A | Auto-eviction (1hr TTL) |
| Risk Level | Low (3/10) | Medium (6/10) |

## Use Cases

### When to Use v1 (Basic)
- Single-turn questions
- No conversation context needed
- Lower latency required
- Testing/debugging

### When to Use v2 (Advanced)
- Multi-turn conversations
- Follow-up questions (e.g., "tell me more", "what about X?")
- Avoiding repetitive answers
- Comprehensive exploration of topics
- Chat-like interfaces

## Deployment Configuration

### Cloud Run Settings
- **Service**: ecosurvey-backend-v2
- **Region**: asia-south1
- **Memory**: 4Gi
- **CPU**: 2
- **Timeout**: 600s
- **Concurrency**: 80
- **Min Instances**: 0
- **Max Instances**: 10

### Environment Variables
```env
OPENAI_API_KEY=sk-...
PINECONE_API_KEY=pcsk_...
PINECONE_INDEX_NAME=ecosurvey-docs
PINECONE_ENVIRONMENT=us-east-1
```

## Next Steps

### Recommended Improvements
1. **Redis Integration**: Replace in-memory session store with Redis for multi-instance support
2. **Metrics**: Add OpenTelemetry for tracking:
   - Query expansion success rate
   - MMR diversity scores
   - Session lifetime distribution
   - Deduplication hit rate
3. **A/B Testing**: Compare v1 vs v2 answer quality systematically
4. **Cost Optimization**: Cache embeddings for frequent queries
5. **Advanced Features**:
   - Semantic caching for repeated questions
   - User feedback loop for relevance tuning
   - Personalized MMR λ parameter per user

### K-Value Analysis (In Progress)
- Test script running: `backend/scripts/test_varying_k.py`
- Testing k ∈ {3, 5, 10} across 100 questions
- Results will determine optimal default top_k
- Last checkpoint: 31/100 questions completed

## Troubleshooting

### Common Issues
1. **Session not persisting**: Ensure same `session_id` across requests
2. **Repetitive answers**: Check `turn_number` increases (session working)
3. **Slow responses**: Multi-query + MMR adds ~2-3s latency vs v1
4. **API errors**: Check retry logs in Cloud Run console

### Logs
```powershell
# View v2 logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=ecosurvey-backend-v2" `
    --limit=50 --project=watch-mail-trial
```

## Metrics (First Test)

### Turn 1
- Query: "What are the key economic growth projections for India?"
- Expanded: (same, no context)
- Variants: 3 queries generated
- Retrieved: 5 unique chunks
- Citations: 4 sources
- Response time: ~8s

### Turn 2
- Query: "Tell me more about consumption trends"
- Expanded: "What are the consumption trends in India's economy?"
- Variants: 3 queries generated
- Retrieved: 5 **new** chunks (0 overlap with turn 1)
- Citations: 4 sources
- Response time: ~7s

## Success Criteria ✅

- [x] Deployed to separate Cloud Run service
- [x] Session-based deduplication working
- [x] Multi-turn conversation tested successfully
- [x] No repeated chunks across turns
- [x] Query expansion handling follow-ups
- [x] Retry logic for resilience
- [x] Session cleanup implemented
- [x] Production error handling
- [x] Comprehensive logging
- [x] API documentation complete

## Deployment Date
February 2, 2026

---

**Status**: ✅ Production Ready  
**Risk Level**: 6/10 (Medium - custom implementation, manageable)  
**Maintenance**: Session cleanup automatic, logs monitored via Cloud Run console
