# Summaries & Claim Cards Skills (Phase 6)

**Goal:** Generate practitioner-quality briefings with evidence-backed claims

---

## 📋 Prerequisites

- Phase 3 (XLSX ingestion) completed
- Phase 4 (Indicator registry) completed
- Phase 5 (PDF ingestion) completed
- LLM API key (OpenAI or Anthropic)
- Understanding of evidence grounding

---

## 🎯 Critical Requirements

**Must handle:**
1. Topic briefings (15-20 per corpus)
2. Claim cards (20-50 per topic)
3. Evidence attachment (≥1 evidence per claim)
4. Retry logic when evidence missing
5. Validation of generated summaries

**STOP CONDITION:**
- Every claim card MUST have ≥1 evidence reference
- If claim card has zero evidence → STOP and regenerate

---

## 🎯 Tasks Breakdown

### **Task 6.1: Verify Data Models**

Already in Phase 1, but verify:

**File: `app/models/summary.py`**

```python
class TopicBrief(Base):
    __tablename__ = 'topic_briefs'
    
    id = Column(Integer, primary_key=True)
    corpus_id = Column(Integer, ForeignKey('corpora.id'))
    topic_key = Column(String)  # e.g., "gdp_growth", "inflation"
    topic_label = Column(String)  # e.g., "GDP Growth"
    brief_text = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class ClaimCard(Base):
    __tablename__ = 'claim_cards'
    
    id = Column(Integer, primary_key=True)
    corpus_id = Column(Integer, ForeignKey('corpora.id'))
    brief_id = Column(Integer, ForeignKey('topic_briefs.id'), nullable=True)
    claim_text = Column(Text)
    confidence = Column(Float)  # 0.0 - 1.0
    evidence = Column(JSONB)  # List of node_ids or table_ids
    created_at = Column(DateTime, default=datetime.utcnow)
```

---

### **Task 6.2: Identify Topics from Corpus**

**File: `ingestion/summaries.py`**

```python
from typing import List, Dict
from sqlalchemy.orm import Session
from app.models.node import Node
from app.models.data import DataTable

def identify_topics(db: Session, corpus_id: int) -> List[Dict[str, str]]:
    """
    Identify key topics from corpus structure.
    
    Strategy:
    1. Extract chapter titles as top-level topics
    2. Extract section titles as sub-topics
    3. Extract table titles as data-driven topics
    
    Returns: List of {topic_key, topic_label}
    """
    topics = []
    
    # Get chapters
    chapters = db.query(Node).filter(
        Node.corpus_id == corpus_id,
        Node.node_type == 'chapter'
    ).all()
    
    for chapter in chapters:
        topic_key = slugify(chapter.title)
        topics.append({
            "topic_key": topic_key,
            "topic_label": chapter.title,
            "source": "chapter",
            "source_id": chapter.id
        })
    
    # Get major sections (those with ≥3 subsections or objects)
    sections = db.query(Node).filter(
        Node.corpus_id == corpus_id,
        Node.node_type == 'section'
    ).all()
    
    for section in sections:
        # Count child nodes
        child_count = db.query(Node).filter(
            Node.corpus_id == corpus_id,
            Node.position > section.position,
            Node.position < section.position + 100  # Within section
        ).count()
        
        if child_count >= 3:
            topic_key = slugify(section.title)
            topics.append({
                "topic_key": topic_key,
                "topic_label": section.title,
                "source": "section",
                "source_id": section.id
            })
    
    # Limit to top 20 topics
    return topics[:20]

def slugify(text: str) -> str:
    """Convert text to slug (gdp_growth, inflation_trends)"""
    import re
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', '_', text)
    return text.strip('_')[:50]
```

---

### **Task 6.3: Generate Topic Briefs with LLM**

**File: `ingestion/summaries.py`**

```python
from openai import OpenAI

def generate_topic_brief(
    db: Session,
    corpus_id: int,
    topic_key: str,
    topic_label: str,
    source_node_id: int
) -> str:
    """
    Generate practitioner-quality brief for topic using LLM.
    
    Output format:
    - 3-5 paragraphs
    - Practitioner-friendly language
    - Evidence-grounded (references included)
    """
    # Get relevant nodes for topic
    nodes = get_topic_nodes(db, corpus_id, source_node_id)
    
    # Get relevant tables
    tables = get_topic_tables(db, corpus_id, topic_label)
    
    # Build context
    context = build_brief_context(nodes, tables)
    
    # Call LLM
    client = OpenAI()
    
    prompt = f"""You are writing a briefing for economic policy practitioners.

Topic: {topic_label}

Context:
{context}

Write a 3-5 paragraph briefing that:
1. Summarizes key findings
2. Highlights important trends
3. Notes policy implications
4. Uses practitioner-friendly language (avoid jargon)
5. References specific evidence (tables, data points)

Format: Plain text, no markdown."""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are an economic policy expert writing briefings."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3
    )
    
    brief_text = response.choices[0].message.content
    return brief_text

def get_topic_nodes(db: Session, corpus_id: int, source_node_id: int) -> List[Node]:
    """Get nodes related to topic (within positional range)"""
    source_node = db.query(Node).get(source_node_id)
    
    # Get nodes within +/- 50 positions
    nodes = db.query(Node).filter(
        Node.corpus_id == corpus_id,
        Node.position >= source_node.position,
        Node.position <= source_node.position + 100
    ).limit(20).all()
    
    return nodes

def get_topic_tables(db: Session, corpus_id: int, topic_label: str) -> List[DataTable]:
    """Get tables related to topic (fuzzy title match)"""
    tables = db.query(DataTable).join(DataFile).filter(
        DataFile.corpus_id == corpus_id
    ).limit(10).all()
    
    # Fuzzy filter by topic keywords
    keywords = set(topic_label.lower().split())
    relevant_tables = []
    
    for table in tables:
        table_keywords = set(table.title.lower().split())
        if keywords & table_keywords:  # Intersection
            relevant_tables.append(table)
    
    return relevant_tables[:5]

def build_brief_context(nodes: List[Node], tables: List[DataTable]) -> str:
    """Build context string for LLM"""
    parts = []
    
    # Add node snippets
    for node in nodes:
        if node.snippet:
            parts.append(f"[{node.node_label}] {node.snippet}")
    
    # Add table summaries
    for table in tables:
        parts.append(f"[{table.title}] {table.notes or 'Data table'}")
    
    return "\n\n".join(parts[:15])  # Limit context size
```

---

### **Task 6.4: Generate Claim Cards with Evidence**

**CRITICAL: Every claim must have ≥1 evidence**

**File: `ingestion/summaries.py`**

```python
import json
from typing import List, Dict

def generate_claim_cards(
    db: Session,
    corpus_id: int,
    brief_id: int,
    topic_label: str
) -> List[Dict]:
    """
    Generate 20-50 claim cards for topic.
    
    STOP CONDITION: If any claim has zero evidence → retry
    """
    # Get nodes and tables for topic
    brief = db.query(TopicBrief).get(brief_id)
    nodes = get_topic_nodes(db, corpus_id, brief.topic_key)
    tables = get_topic_tables(db, corpus_id, topic_label)
    
    # Build context
    context = build_claim_context(nodes, tables)
    
    # Call LLM with strict JSON schema
    client = OpenAI()
    
    prompt = f"""Generate evidence-backed claim cards for: {topic_label}

Context:
{context}

Generate 20-30 specific, factual claims. Each claim MUST:
1. Be a single sentence
2. Reference specific evidence (node_id or table_id)
3. Be verifiable from context

Output JSON array:
[
  {{
    "claim_text": "GDP growth accelerated to 7.2% in FY2023",
    "confidence": 0.9,
    "evidence": [{{"type": "table", "id": 5}}]
  }},
  ...
]
"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You generate evidence-backed claims as JSON."},
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"},
        temperature=0.2
    )
    
    claims_data = json.loads(response.choices[0].message.content)
    claims = claims_data.get("claims", [])
    
    # Validate evidence
    validated_claims = []
    for claim in claims:
        if not claim.get("evidence") or len(claim["evidence"]) == 0:
            print(f"⚠️  Claim missing evidence: {claim['claim_text'][:50]}...")
            # STOP CONDITION: Retry or skip
            continue
        
        validated_claims.append(claim)
    
    if len(validated_claims) < 10:
        print("❌ STOP: Too few valid claims generated (< 10)")
        return []
    
    return validated_claims

def build_claim_context(nodes: List[Node], tables: List[DataTable]) -> str:
    """Build context with IDs for evidence linking"""
    parts = []
    
    for node in nodes:
        parts.append(f"[node_id:{node.id}] {node.node_label}: {node.snippet}")
    
    for table in tables:
        parts.append(f"[table_id:{table.id}] {table.title}")
    
    return "\n".join(parts[:20])
```

---

### **Task 6.5: Store Summaries in Database**

**File: `ingestion/summaries.py`**

```python
from app.models.summary import TopicBrief, ClaimCard

def store_topic_brief(
    db: Session,
    corpus_id: int,
    topic_key: str,
    topic_label: str,
    brief_text: str
) -> int:
    """Store topic brief in database"""
    brief = TopicBrief(
        corpus_id=corpus_id,
        topic_key=topic_key,
        topic_label=topic_label,
        brief_text=brief_text
    )
    db.add(brief)
    db.commit()
    db.refresh(brief)
    
    print(f"✓ Stored brief: {topic_label} (id={brief.id})")
    return brief.id

def store_claim_cards(
    db: Session,
    corpus_id: int,
    brief_id: int,
    claims: List[Dict]
) -> int:
    """Store claim cards in database"""
    count = 0
    
    for claim_data in claims:
        claim = ClaimCard(
            corpus_id=corpus_id,
            brief_id=brief_id,
            claim_text=claim_data["claim_text"],
            confidence=claim_data.get("confidence", 0.8),
            evidence=claim_data["evidence"]  # JSONB array
        )
        db.add(claim)
        count += 1
    
    db.commit()
    print(f"✓ Stored {count} claim cards for brief {brief_id}")
    return count
```

---

### **Task 6.6: Main Ingestion Script**

**File: `ingestion/summaries.py`**

```python
def ingest_summaries(corpus_id: int):
    """Main entry point for summaries ingestion"""
    db = SessionLocal()
    
    try:
        # Identify topics
        topics = identify_topics(db, corpus_id)
        print(f"✓ Identified {len(topics)} topics")
        
        # Generate briefs
        for topic in topics:
            print(f"\n📝 Generating brief: {topic['topic_label']}")
            
            brief_text = generate_topic_brief(
                db,
                corpus_id,
                topic["topic_key"],
                topic["topic_label"],
                topic["source_id"]
            )
            
            brief_id = store_topic_brief(
                db,
                corpus_id,
                topic["topic_key"],
                topic["topic_label"],
                brief_text
            )
            
            # Generate claim cards
            print(f"🔖 Generating claim cards for: {topic['topic_label']}")
            claims = generate_claim_cards(
                db,
                corpus_id,
                brief_id,
                topic["topic_label"]
            )
            
            if not claims:
                print(f"❌ STOP: No valid claims generated for {topic['topic_label']}")
                continue
            
            store_claim_cards(db, corpus_id, brief_id, claims)
        
        print(f"\n✅ Summaries ingestion complete for corpus {corpus_id}")
        
    finally:
        db.close()

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python -m ingestion.summaries <corpus_id>")
        sys.exit(1)
    
    corpus_id = int(sys.argv[1])
    ingest_summaries(corpus_id)
```

---

### **Task 6.7: Retry Logic for Failed Claims**

**File: `ingestion/summaries.py`**

```python
def generate_claim_cards_with_retry(
    db: Session,
    corpus_id: int,
    brief_id: int,
    topic_label: str,
    max_retries: int = 3
) -> List[Dict]:
    """
    Generate claim cards with retry logic.
    Retry if < 10 valid claims or > 50% claims missing evidence.
    """
    for attempt in range(max_retries):
        print(f"  Attempt {attempt + 1}/{max_retries}")
        
        claims = generate_claim_cards(db, corpus_id, brief_id, topic_label)
        
        if len(claims) >= 10:
            # Success
            return claims
        
        print(f"  ⚠️  Only {len(claims)} valid claims, retrying...")
    
    # Final attempt failed
    print(f"❌ STOP: Failed to generate valid claims after {max_retries} attempts")
    return []
```

---

## ✅ Acceptance Criteria

### **Test 1: Topic Briefs Generated**
```bash
python -m ingestion.summaries 1
```

**Verify:**
```sql
SELECT topic_label, LENGTH(brief_text) as chars
FROM topic_briefs
WHERE corpus_id = 1;
```

**Expected:**
- 15-20 topic briefs
- Each brief 500-2000 chars
- Topics match corpus structure

---

### **Test 2: Claim Cards with Evidence (CRITICAL)**
```sql
SELECT 
    COUNT(*) as total_claims,
    COUNT(CASE WHEN jsonb_array_length(evidence) = 0 THEN 1 END) as claims_without_evidence
FROM claim_cards
WHERE corpus_id = 1;
```

**Expected:**
- total_claims: 300-600 (20-50 per topic)
- claims_without_evidence: **0** (STOP CONDITION)

**STOP CONDITION:** If claims_without_evidence > 0 → STOP and regenerate

---

### **Test 3: Evidence Distribution**
```sql
SELECT 
    jsonb_array_length(evidence) as evidence_count,
    COUNT(*) as claim_count
FROM claim_cards
WHERE corpus_id = 1
GROUP BY evidence_count
ORDER BY evidence_count;
```

**Expected distribution:**
- 1 evidence: 60-70% of claims
- 2 evidence: 20-30% of claims
- 3+ evidence: 5-10% of claims

---

### **Test 4: Briefing API Endpoint**

Create API endpoint to test retrieval:

**File: `app/api/briefing.py`**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.summary import TopicBrief, ClaimCard

router = APIRouter()

@router.get("/corpus/{corpus_id}/briefing")
def get_corpus_briefing(corpus_id: int, db: Session = Depends(get_db)):
    """Get all topic briefs and claim cards for corpus"""
    briefs = db.query(TopicBrief).filter(
        TopicBrief.corpus_id == corpus_id
    ).all()
    
    if not briefs:
        raise HTTPException(status_code=404, detail="No briefs found")
    
    result = []
    for brief in briefs:
        claims = db.query(ClaimCard).filter(
            ClaimCard.brief_id == brief.id
        ).all()
        
        result.append({
            "topic_key": brief.topic_key,
            "topic_label": brief.topic_label,
            "brief_text": brief.brief_text,
            "claims": [
                {
                    "claim_text": c.claim_text,
                    "confidence": c.confidence,
                    "evidence": c.evidence
                }
                for c in claims
            ]
        })
    
    return {"corpus_id": corpus_id, "topics": result}
```

**Test:**
```bash
curl http://localhost:8000/api/corpus/1/briefing | jq '.topics | length'
```

**Expected:** 15-20 topics

---

## 📝 Deliverables Checklist

- [ ] Topic identification working
- [ ] Topic briefs generated (15-20 per corpus)
- [ ] Claim cards generated (20-50 per topic)
- [ ] Every claim has ≥1 evidence
- [ ] Retry logic implemented
- [ ] Briefing API endpoint working
- [ ] All acceptance tests passing

---

## 🔗 Next Phase

Once all deliverables complete and stop condition verified:
- **Phase 7: Chat Retrieval & Context Pack** (query classification, retrieval, token budgets)
