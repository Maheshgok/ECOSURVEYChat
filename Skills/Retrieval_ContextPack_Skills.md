# Retrieval & Context Pack Skills (Phase 7)

**Goal:** Fast, grounded practitioner responses with strict token budgets

---

## 📋 Prerequisites

- Phase 5 (PDF ingestion with embeddings) completed
- Phase 6 (Summaries) completed
- LLM API key configured
- Understanding of Section 9.4 (Context Pack Assembly)

---

## 🎯 Critical Requirements

**Context Pack Assembly (Section 9.4):**
- Global budget: `CONTEXT_BUDGET_TOKENS` (default 10,000)
- Quotas:
  - Conversation memory: 500 tokens (last 3 user + 3 assistant turns)
  - Claims/briefs: 1,500 tokens
  - Narrative: 4,000 tokens
  - Data: 4,000 tokens
- Supplements: ≤25% of narrative quota unless explicitly requested
- "Must-include": Explicitly referenced objects (Table I.2a, Box I.1)

**STOP CONDITIONS:**
1. Context pack exceeds CONTEXT_BUDGET_TOKENS → STOP
2. Explicitly referenced evidence missing from pack → STOP
3. Supplement quota violated (>25%) → STOP
4. Uncited numeric claim in response → STOP

---

## 🎯 Tasks Breakdown

### **Task 7.1: Query Classifier**

**File: `app/services/retrieval.py`**

```python
from enum import Enum

class QueryType(Enum):
    DATA = "data"  # Asks for specific numbers/tables
    NARRATIVE = "narrative"  # Asks for explanations/context
    MIXED = "mixed"  # Combination

def classify_query(question: str) -> QueryType:
    """
    Classify user question as data vs narrative.
    
    Data queries: contain numbers, "how much", "what is the value"
    Narrative queries: "why", "how", "explain"
    """
    question_lower = question.lower()
    
    data_keywords = [
        'how much', 'what is the', 'value', 'number', 'percent',
        'rate of', 'growth rate', 'data', 'statistics', 'figure'
    ]
    
    narrative_keywords = [
        'why', 'how', 'explain', 'describe', 'what are the reasons',
        'what factors', 'implications', 'impact'
    ]
    
    data_score = sum(1 for kw in data_keywords if kw in question_lower)
    narrative_score = sum(1 for kw in narrative_keywords if kw in question_lower)
    
    if data_score > narrative_score:
        return QueryType.DATA
    elif narrative_score > data_score:
        return QueryType.NARRATIVE
    else:
        return QueryType.MIXED
```

---

### **Task 7.2: Retrieval Pipeline**

**File: `app/services/retrieval.py`**

```python
from typing import List, Dict
from sqlalchemy.orm import Session
from app.models.node import Node
from app.models.search import SearchIndex, Embedding

def retrieve_evidence(
    db: Session,
    corpus_id: int,
    question: str,
    query_type: QueryType,
    top_k: int = 20
) -> List[Dict]:
    """
    Retrieve evidence using hybrid search (FTS + vector).
    
    Returns: List of evidence items with scores
    """
    # Full-text search
    fts_results = fts_search(db, corpus_id, question, top_k)
    
    # Vector search
    vector_results = vector_search(db, corpus_id, question, top_k)
    
    # Merge and rank
    merged = merge_results(fts_results, vector_results)
    
    # Filter by query type
    if query_type == QueryType.DATA:
        # Prioritize tables, data-heavy nodes
        merged = prioritize_data_evidence(merged)
    elif query_type == QueryType.NARRATIVE:
        # Prioritize sections, paragraphs
        merged = prioritize_narrative_evidence(merged)
    
    return merged[:top_k]

def fts_search(db: Session, corpus_id: int, question: str, top_k: int) -> List[Dict]:
    """Full-text search using PostgreSQL tsvector"""
    from sqlalchemy import func
    
    results = db.query(
        SearchIndex.node_id,
        func.ts_rank(SearchIndex.search_vector, func.plainto_tsquery(question)).label('score')
    ).filter(
        SearchIndex.corpus_id == corpus_id
    ).order_by(func.ts_rank(SearchIndex.search_vector, func.plainto_tsquery(question)).desc()).limit(top_k).all()
    
    return [{"node_id": r.node_id, "fts_score": float(r.score)} for r in results]

def vector_search(db: Session, corpus_id: int, question: str, top_k: int) -> List[Dict]:
    """Vector search using pgvector cosine similarity"""
    from openai import OpenAI
    
    client = OpenAI()
    
    # Embed question
    response = client.embeddings.create(
        input=question,
        model="text-embedding-3-large"
    )
    question_vector = response.data[0].embedding
    
    # Cosine similarity search
    from sqlalchemy import func
    
    results = db.query(
        Embedding.node_id,
        (1 - func.cosine_distance(Embedding.embedding_vector, question_vector)).label('similarity')
    ).filter(
        Embedding.corpus_id == corpus_id
    ).order_by(func.cosine_distance(Embedding.embedding_vector, question_vector)).limit(top_k).all()
    
    return [{"node_id": r.node_id, "vector_score": float(r.similarity)} for r in results]

def merge_results(fts_results: List[Dict], vector_results: List[Dict]) -> List[Dict]:
    """Merge FTS and vector results with reciprocal rank fusion"""
    scores = {}
    
    for rank, item in enumerate(fts_results):
        node_id = item["node_id"]
        scores[node_id] = scores.get(node_id, 0) + 1 / (rank + 1)
    
    for rank, item in enumerate(vector_results):
        node_id = item["node_id"]
        scores[node_id] = scores.get(node_id, 0) + 1 / (rank + 1)
    
    # Sort by combined score
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    
    return [{"node_id": node_id, "score": score} for node_id, score in ranked]
```

---

### **Task 7.3: Graph Expansion**

**File: `app/services/retrieval.py`**

```python
def expand_with_graph(
    db: Session,
    corpus_id: int,
    initial_nodes: List[int]
) -> List[int]:
    """
    Expand initial nodes via refers_to and supports edges (depth 1 only).
    
    Returns: List of node_ids (initial + expanded)
    """
    from app.models.edge import Edge
    
    expanded_ids = set(initial_nodes)
    
    # Get edges where source is in initial_nodes
    edges = db.query(Edge).filter(
        Edge.corpus_id == corpus_id,
        Edge.source_node_id.in_(initial_nodes),
        Edge.rel_type.in_(['refers_to', 'supports'])
    ).all()
    
    for edge in edges:
        if edge.target_node_id:
            expanded_ids.add(edge.target_node_id)
    
    return list(expanded_ids)
```

---

### **Task 7.4: Context Pack Assembly (CRITICAL)**

**File: `app/services/context_pack.py`**

```python
from dataclasses import dataclass
from typing import List, Dict

@dataclass
class ContextQuotas:
    conversation: int = 500
    claims_briefs: int = 1500
    narrative: int = 4000
    data: int = 4000
    total: int = 10000

def assemble_context_pack(
    db: Session,
    corpus_id: int,
    question: str,
    conversation_history: List[Dict],
    retrieved_evidence: List[Dict],
    quotas: ContextQuotas = ContextQuotas()
) -> Dict:
    """
    Assemble context pack with strict token budgets.
    
    STOP CONDITIONS:
    1. Total tokens exceed quotas.total → STOP
    2. Explicitly referenced object missing → STOP
    3. Supplement quota violated → STOP
    
    Returns:
    {
        "conversation": [...],
        "claims": [...],
        "narrative": [...],
        "data": [...],
        "total_tokens": int,
        "explicitly_referenced": [...]
    }
    """
    pack = {
        "conversation": [],
        "claims": [],
        "narrative": [],
        "data": [],
        "total_tokens": 0,
        "explicitly_referenced": []
    }
    
    # Extract explicit references from question (Table I.2a, Box I.1, etc.)
    explicit_refs = extract_explicit_references(question)
    
    # 1. Add conversation memory (last 3+3 turns)
    conv_text = format_conversation_memory(conversation_history, max_turns=6)
    conv_tokens = count_tokens(conv_text)
    
    if conv_tokens > quotas.conversation:
        conv_text = truncate_to_tokens(conv_text, quotas.conversation)
        conv_tokens = quotas.conversation
    
    pack["conversation"] = conv_text
    pack["total_tokens"] += conv_tokens
    
    # 2. Add explicitly referenced items (MUST-INCLUDE)
    for ref in explicit_refs:
        item = find_reference(db, corpus_id, ref)
        if not item:
            # STOP CONDITION: Explicit reference not found
            raise ValueError(f"STOP: Explicitly referenced {ref} not found in corpus")
        
        item_text = format_evidence_item(item)
        item_tokens = count_tokens(item_text)
        
        pack["explicitly_referenced"].append(item_text)
        pack["total_tokens"] += item_tokens
        
        if pack["total_tokens"] > quotas.total:
            raise ValueError(f"STOP: Context pack exceeds budget ({pack['total_tokens']} > {quotas.total})")
    
    # 3. Add claims/briefs (up to quota)
    claims_text = get_relevant_claims(db, corpus_id, question)
    claims_tokens = count_tokens(claims_text)
    
    if claims_tokens > quotas.claims_briefs:
        claims_text = truncate_to_tokens(claims_text, quotas.claims_briefs)
        claims_tokens = quotas.claims_briefs
    
    pack["claims"] = claims_text
    pack["total_tokens"] += claims_tokens
    
    # 4. Add narrative evidence (prioritize primary, cap supplements at 25%)
    narrative_budget = quotas.narrative - sum(count_tokens(pack["explicitly_referenced"]))
    narrative_items = []
    supplement_tokens = 0
    
    for evidence in retrieved_evidence:
        node = db.query(Node).get(evidence["node_id"])
        if not node:
            continue
        
        # Check if supplement
        doc = db.query(Document).get(node.document_id)
        is_supplement = (doc.role == 'supplement')
        
        item_text = format_evidence_item(node)
        item_tokens = count_tokens(item_text)
        
        # Check supplement quota
        if is_supplement:
            if supplement_tokens + item_tokens > narrative_budget * 0.25:
                # STOP CONDITION: Supplement quota exceeded
                continue
            supplement_tokens += item_tokens
        
        # Check total budget
        if pack["total_tokens"] + item_tokens > quotas.total:
            break
        
        narrative_items.append(item_text)
        pack["total_tokens"] += item_tokens
    
    pack["narrative"] = "\n\n".join(narrative_items)
    
    # 5. Add data evidence (tables)
    data_budget = quotas.data
    data_items = get_relevant_tables(db, corpus_id, question, data_budget)
    data_tokens = count_tokens(data_items)
    
    if pack["total_tokens"] + data_tokens > quotas.total:
        data_items = truncate_to_tokens(data_items, quotas.total - pack["total_tokens"])
        data_tokens = count_tokens(data_items)
    
    pack["data"] = data_items
    pack["total_tokens"] += data_tokens
    
    # Final validation
    if pack["total_tokens"] > quotas.total:
        raise ValueError(f"STOP: Context pack exceeds budget ({pack['total_tokens']} > {quotas.total})")
    
    return pack

def extract_explicit_references(question: str) -> List[str]:
    """Extract Table I.2a, Box I.1, Chart I.21 from question"""
    import re
    patterns = [
        r'Table\s+[IVX]+\.\d+[a-z]?',
        r'Box\s+[IVX]+\.\d+',
        r'Chart\s+[IVX]+\.\d+[a-z]?'
    ]
    
    refs = []
    for pattern in patterns:
        refs.extend(re.findall(pattern, question, re.IGNORECASE))
    
    return refs

def count_tokens(text: str) -> int:
    """Estimate token count (rough: 1 token ≈ 4 chars)"""
    return len(text) // 4

def truncate_to_tokens(text: str, max_tokens: int) -> str:
    """Truncate text to token budget"""
    max_chars = max_tokens * 4
    return text[:max_chars] + "..." if len(text) > max_chars else text
```

---

### **Task 7.5: Response Validation**

**File: `app/services/validation.py`**

```python
import re

def validate_response(response_json: Dict) -> bool:
    """
    Validate LLM response for uncited claims.
    
    STOP CONDITION: If numeric claim without citation → reject
    """
    answer = response_json.get("answer", "")
    evidence = response_json.get("evidence", [])
    
    # Extract numeric claims
    numeric_patterns = [
        r'\d+\.?\d*%',  # 7.2%
        r'\$\d+\.?\d*[MBT]?',  # $5.2B
        r'\d+\.?\d*\s*(million|billion|trillion)',
    ]
    
    for pattern in numeric_patterns:
        matches = re.findall(pattern, answer, re.IGNORECASE)
        if matches and not evidence:
            # STOP CONDITION: Numeric claim without evidence
            return False
    
    return True
```

---

## ✅ Acceptance Criteria

### **Test 1: Context Pack Token Budget**
```python
pack = assemble_context_pack(db, 1, "What is GDP growth?", [], evidence)
assert pack["total_tokens"] <= 10000, "STOP: Budget exceeded"
```

### **Test 2: Explicit Reference Inclusion**
```python
pack = assemble_context_pack(db, 1, "Show me Table I.2a", [], evidence)
assert any("Table I.2a" in item for item in pack["explicitly_referenced"]), "STOP: Missing reference"
```

### **Test 3: Supplement Quota**
```python
pack = assemble_context_pack(db, 1, "Explain inflation", [], evidence)
supplement_tokens = sum(count_tokens(item) for item in pack["narrative"] if is_supplement(item))
assert supplement_tokens <= 4000 * 0.25, "STOP: Supplement quota exceeded"
```

---

## 📝 Deliverables

- [ ] Query classifier working
- [ ] Hybrid retrieval (FTS + vector) implemented
- [ ] Graph expansion (depth 1) working
- [ ] Context pack assembly with quotas
- [ ] All stop conditions enforced
- [ ] Response validation implemented

---

## 🔗 Next Phase

- **Phase 7 (Part 2): Chat API & Streaming** (SSE implementation)
