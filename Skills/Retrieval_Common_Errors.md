# Retrieval & Context Pack Common Errors (Phase 7)

**Reference:** Skills/Retrieval_ContextPack_Skills.md

---

## Error 1: Context Pack Exceeds Budget (STOP CONDITION)

**Symptom:** Context pack has 12,000 tokens (> 10,000 limit)

**Cause:** No cumulative token tracking

**Fix:**
```python
# In assemble_context_pack(), track cumulative:
pack["total_tokens"] = 0

# After each section:
pack["total_tokens"] += count_tokens(section_text)

if pack["total_tokens"] > quotas.total:
    raise ValueError(f"STOP: Budget exceeded ({pack['total_tokens']} > {quotas.total})")
```

**Verification:**
```python
pack = assemble_context_pack(...)
assert pack["total_tokens"] <= 10000, "STOP: Budget exceeded"
```

---

## Error 2: Explicit Reference Missing (STOP CONDITION)

**Symptom:** User asks "Show me Table I.2a" but response doesn't include it

**Cause:** `extract_explicit_references()` not detecting reference

**Fix:**
```python
def extract_explicit_references(question: str) -> List[str]:
    patterns = [
        r'Table\s+[IVX]+\.\d+[a-z]?',
        r'Box\s+[IVX]+\.\d+',
        r'Chart\s+[IVX]+\.\d+[a-z]?',
    ]
    
    refs = []
    for pattern in patterns:
        matches = re.findall(pattern, question, re.IGNORECASE)
        refs.extend([m.strip() for m in matches])
    
    return refs
```

**Verification:** If explicit reference not found in corpus → STOP immediately

---

## Error 3: Supplement Quota Exceeded (STOP CONDITION)

**Symptom:** Supplements take 60% of narrative quota (> 25% limit)

**Cause:** No supplement tracking

**Fix:**
```python
supplement_tokens = 0
narrative_budget = quotas.narrative

for evidence in retrieved_evidence:
    node = db.query(Node).get(evidence["node_id"])
    doc = db.query(Document).get(node.document_id)
    
    is_supplement = (doc.role == 'supplement')
    item_tokens = count_tokens(format_evidence_item(node))
    
    if is_supplement:
        if supplement_tokens + item_tokens > narrative_budget * 0.25:
            # STOP: Supplement quota exceeded
            continue
        supplement_tokens += item_tokens
```

---

## Error 4: Vector Search Slow

**Symptom:** Retrieval takes 5+ seconds

**Cause:** No pgvector index

**Fix:**
```sql
-- In migrations.sql:
CREATE INDEX embeddings_vector_idx 
ON embeddings 
USING ivfflat (embedding_vector vector_cosine_ops) 
WITH (lists = 100);
```

---

## Error 5: FTS Search Returns Nothing

**Symptom:** `fts_search()` returns []

**Cause:** search_index table not populated

**Fix:**
```python
# After PDF ingestion, populate search_index:
from app.models.search import SearchIndex

for node in nodes:
    search_text = f"{node.title} {node.snippet} {node.full_text}"
    
    search_record = SearchIndex(
        corpus_id=corpus_id,
        node_id=node.id,
        search_vector=func.to_tsvector('english', search_text)
    )
    db.add(search_record)
```

---

## Error 6: Query Classifier Wrong

**Symptom:** "How much is GDP?" classified as NARRATIVE (should be DATA)

**Cause:** Keyword list incomplete

**Fix:**
```python
data_keywords = [
    'how much', 'what is the', 'value', 'number', 'percent',
    'rate', 'growth rate', 'data', 'statistics', 'figure',
    'amount', 'total', 'current'  # ADD MORE
]
```

---

## Error 7: Graph Expansion Includes Wrong Edges

**Symptom:** Context pack includes unrelated nodes

**Cause:** Expanding on "contains" edges (should only use refers_to, supports)

**Fix:**
```python
# In expand_with_graph():
edges = db.query(Edge).filter(
    Edge.source_node_id.in_(initial_nodes),
    Edge.rel_type.in_(['refers_to', 'supports'])  # NOT 'contains'
).all()
```

---

## Error 8: Conversation Memory Truncated Badly

**Symptom:** Last turn cut off mid-sentence

**Cause:** Character-based truncation

**Fix:**
```python
def truncate_to_tokens(text: str, max_tokens: int) -> str:
    # Truncate at sentence boundary
    max_chars = max_tokens * 4
    if len(text) <= max_chars:
        return text
    
    truncated = text[:max_chars]
    
    # Find last period
    last_period = truncated.rfind('.')
    if last_period > max_chars * 0.8:  # At least 80% of content
        return truncated[:last_period + 1]
    
    return truncated + "..."
```

---

## Error 9: Retrieval Returns Duplicates

**Symptom:** Same node appears 3 times in retrieved_evidence

**Cause:** No deduplication in merge_results

**Fix:**
```python
def merge_results(fts_results, vector_results):
    scores = {}  # node_id → score
    
    for item in fts_results + vector_results:
        node_id = item["node_id"]
        scores[node_id] = max(scores.get(node_id, 0), item.get("score", 0))
    
    # Return unique nodes only
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [{"node_id": nid, "score": score} for nid, score in ranked]
```

---

## Error 10: Claims Not Retrieved

**Symptom:** Context pack has no claims/briefs

**Cause:** `get_relevant_claims()` not querying claim_cards table

**Fix:**
```python
def get_relevant_claims(db: Session, corpus_id: int, question: str) -> str:
    # Get relevant claim cards
    claims = db.query(ClaimCard).filter(
        ClaimCard.corpus_id == corpus_id
    ).limit(20).all()
    
    # Format claims
    claim_texts = [f"- {c.claim_text}" for c in claims]
    return "\n".join(claim_texts)
```

---

## Error 11: Token Count Inaccurate

**Symptom:** Context pack "10,000 tokens" actually 15,000 tokens when sent to LLM

**Cause:** Rough estimation (1 token ≈ 4 chars) too inaccurate

**Fix:**
```python
import tiktoken

def count_tokens(text: str, model: str = "gpt-4") -> int:
    encoding = tiktoken.encoding_for_model(model)
    return len(encoding.encode(text))
```

---

## Error 12: Uncited Numeric Claim (STOP CONDITION)

**Symptom:** Response says "GDP grew 7.2%" but evidence list is empty

**Cause:** Response validation not enforced

**Fix:**
```python
# After getting LLM response:
from app.services.validation import validate_response

if not validate_response(response_json):
    # STOP: Uncited claim detected
    raise ValueError("STOP: Response contains uncited numeric claims")
```

---

## Error 13: Missing Table Data

**Symptom:** Context pack includes tables but no actual data

**Cause:** `get_relevant_tables()` returns titles only

**Fix:**
```python
def get_relevant_tables(db, corpus_id, question, token_budget):
    tables = db.query(DataTable).join(DataFile).filter(
        DataFile.corpus_id == corpus_id
    ).limit(5).all()
    
    formatted = []
    for table in tables:
        # Include table_json data
        data_preview = json.dumps(table.table_json)[:500]  # First 500 chars
        formatted.append(f"{table.title}\n{data_preview}")
    
    return "\n\n".join(formatted)
```

---

## Debugging Checklist

- [ ] Context pack total_tokens <= 10,000
- [ ] Explicit references included
- [ ] Supplement quota <= 25%
- [ ] Vector search has index
- [ ] FTS search_index populated
- [ ] Query classifier accurate
- [ ] Graph expansion correct (refers_to, supports only)
- [ ] Conversation memory well-truncated
- [ ] No duplicate nodes in retrieval
- [ ] Claims retrieved
- [ ] Token count accurate (use tiktoken)
- [ ] Uncited claims detected
- [ ] Tables include data

---

## Escalation

If budget keeps exceeding:
1. Print token breakdown by section
2. Reduce quotas proportionally
3. Prioritize must-include items first
4. Truncate less critical sections earlier
