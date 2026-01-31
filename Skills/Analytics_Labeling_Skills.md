# Analytics & Labeling Skills (Phase 8)

**Goal:** Measure usage, sentiment, and coverage gaps with offline labeling jobs

---

## 📋 Prerequisites

- Phase 7 (Chat API) completed
- Chat logs populated (conversations, messages, retrieval_events)
- LLM API for labeling
- Understanding of analytics requirements (Section 10)

---

## 🎯 Critical Requirements

**Runtime logging:**
- conversations, messages, retrieval_events (with full citation data)

**Offline labeling job:**
- Classify messages: topics, entities, intent, sentiment, concerns
- Store in message_labels with confidence scores

**Offline clustering job (weekly):**
- Embed user questions
- Cluster into themes
- Store in topic_clusters with summaries

**Offline rollup job (daily):**
- Compute daily_insights:
  - total_questions
  - top_topics (top 5)
  - top_concerns (top 3)
  - sentiment_mix (optimistic/neutral/pessimistic/mixed percentages)
  - notable_questions (interesting/complex queries)
  - coverage_gaps (questions with low evidence coverage)

---

## 🎯 Tasks Breakdown

### **Task 8.1: Runtime Logging**

**File: `app/services/chat_service.py`**

```python
from app.models.analytics import Conversation, Message, RetrievalEvent

def create_conversation(db: Session, corpus_id: int, question: str) -> int:
    """Create conversation and log first message"""
    # Create conversation
    conversation = Conversation(
        corpus_id=corpus_id,
        started_at=datetime.utcnow()
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    
    # Log user message
    user_message = Message(
        conversation_id=conversation.id,
        role="user",
        content=question,
        tokens=count_tokens(question)
    )
    db.add(user_message)
    db.commit()
    
    return conversation.id

def log_retrieval_events(
    db: Session,
    conversation_id: int,
    message_id: int,
    evidence: List[Dict]
):
    """Log retrieval events with full citation data"""
    for item in evidence:
        event = RetrievalEvent(
            conversation_id=conversation_id,
            message_id=message_id,
            node_id=item.get("node_id"),
            table_id=item.get("table_id"),
            rank=item.get("rank"),
            score=item.get("score"),
            used_in_response=item.get("used", False),
            metadata={"citation": item.get("citation")}
        )
        db.add(event)
    
    db.commit()
```

---

### **Task 8.2: Offline Labeling Job**

**File: `ingestion/label_messages.py`**

```python
from openai import OpenAI
import json

def label_messages_batch(db: Session, corpus_id: int, batch_size: int = 100):
    """
    Label unlabeled messages in corpus.
    
    Classifies:
    - topics (list of topic keys)
    - entities (GDP, inflation, FDI, etc.)
    - intent (data_request, explanation_request, comparison, etc.)
    - sentiment (optimistic, neutral, pessimistic, mixed)
    - concerns (list of concern keywords)
    """
    # Get unlabeled messages
    unlabeled = db.query(Message).filter(
        Message.role == "user",
        ~Message.id.in_(
            db.query(MessageLabel.message_id)
        )
    ).join(Conversation).filter(
        Conversation.corpus_id == corpus_id
    ).limit(batch_size).all()
    
    if not unlabeled:
        print("✓ All messages labeled")
        return
    
    client = OpenAI()
    
    for message in unlabeled:
        # Call LLM for classification
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Cheaper model for labeling
            messages=[
                {"role": "system", "content": LABELING_SYSTEM_PROMPT},
                {"role": "user", "content": f"Classify this question:\n\n{message.content}"}
            ],
            response_format={"type": "json_object"},
            temperature=0.1
        )
        
        labels = json.loads(response.choices[0].message.content)
        
        # Store labels
        message_label = MessageLabel(
            message_id=message.id,
            topics=labels.get("topics", []),
            entities=labels.get("entities", []),
            intent=labels.get("intent"),
            sentiment=labels.get("sentiment"),
            concerns=labels.get("concerns", []),
            confidence=labels.get("confidence", 0.8)
        )
        db.add(message_label)
    
    db.commit()
    print(f"✓ Labeled {len(unlabeled)} messages")

LABELING_SYSTEM_PROMPT = """You classify user questions about economic surveys.

Output JSON:
{
    "topics": ["gdp_growth", "inflation"],  // Relevant topics
    "entities": ["GDP", "CPI", "FDI"],      // Economic indicators mentioned
    "intent": "data_request",               // data_request, explanation_request, comparison, trend_analysis
    "sentiment": "neutral",                 // optimistic, neutral, pessimistic, mixed
    "concerns": ["slowdown", "rising costs"], // User concerns
    "confidence": 0.9
}

Sentiment definitions:
- optimistic: Question implies positive outlook
- pessimistic: Question implies concerns/negative outlook
- neutral: Factual/informational
- mixed: Both positive and negative aspects"""
```

---

### **Task 8.3: Offline Clustering Job**

**File: `ingestion/cluster_topics.py`**

```python
from sklearn.cluster import KMeans
from openai import OpenAI
import numpy as np

def cluster_questions(db: Session, corpus_id: int, time_window_days: int = 7):
    """
    Cluster recent questions into themes (weekly job).
    
    Steps:
    1. Get questions from last 7 days
    2. Embed questions
    3. Cluster with K-means
    4. Generate cluster summaries
    5. Store in topic_clusters
    """
    # Get recent messages
    cutoff = datetime.utcnow() - timedelta(days=time_window_days)
    
    messages = db.query(Message).filter(
        Message.role == "user",
        Message.created_at >= cutoff
    ).join(Conversation).filter(
        Conversation.corpus_id == corpus_id
    ).all()
    
    if len(messages) < 10:
        print("⚠️  Not enough messages for clustering")
        return
    
    # Embed questions
    client = OpenAI()
    
    questions = [m.content for m in messages]
    
    response = client.embeddings.create(
        input=questions,
        model="text-embedding-3-small"  // Cheaper for clustering
    )
    
    embeddings = np.array([r.embedding for r in response.data])
    
    # Cluster
    n_clusters = min(5, len(messages) // 5)  # Max 5 clusters
    kmeans = KMeans(n_clusters=n_clusters, random_state=42)
    labels = kmeans.fit_predict(embeddings)
    
    # Generate cluster summaries
    for cluster_id in range(n_clusters):
        cluster_questions = [questions[i] for i in range(len(questions)) if labels[i] == cluster_id]
        
        if not cluster_questions:
            continue
        
        # Generate summary
        summary_prompt = f"""Summarize this cluster of user questions (1 sentence):

{chr(10).join(f'- {q}' for q in cluster_questions[:10])}

Output: Short theme label"""
        
        summary_response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": summary_prompt}],
            temperature=0.2
        )
        
        theme = summary_response.choices[0].message.content
        
        # Store cluster
        cluster_record = TopicCluster(
            corpus_id=corpus_id,
            cluster_id=cluster_id,
            theme=theme,
            question_count=len(cluster_questions),
            sample_questions=cluster_questions[:5],
            created_at=datetime.utcnow()
        )
        db.add(cluster_record)
    
    db.commit()
    print(f"✓ Created {n_clusters} topic clusters")
```

---

### **Task 8.4: Daily Insights Rollup**

**File: `ingestion/daily_rollup.py`**

```python
def compute_daily_insights(db: Session, corpus_id: int, date: datetime.date):
    """
    Compute daily insights rollup.
    
    Computes:
    - total_questions
    - top_topics (top 5)
    - top_concerns (top 3)
    - sentiment_mix (percentages)
    - notable_questions (interesting queries)
    - coverage_gaps (low evidence questions)
    """
    # Get messages for date
    start = datetime.combine(date, datetime.min.time())
    end = start + timedelta(days=1)
    
    messages = db.query(Message).filter(
        Message.role == "user",
        Message.created_at >= start,
        Message.created_at < end
    ).join(Conversation).filter(
        Conversation.corpus_id == corpus_id
    ).all()
    
    if not messages:
        print(f"No messages on {date}")
        return
    
    message_ids = [m.id for m in messages]
    
    # Get labels
    labels = db.query(MessageLabel).filter(
        MessageLabel.message_id.in_(message_ids)
    ).all()
    
    # Compute metrics
    total_questions = len(messages)
    
    # Top topics
    topic_counts = {}
    for label in labels:
        for topic in label.topics or []:
            topic_counts[topic] = topic_counts.get(topic, 0) + 1
    
    top_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    
    # Top concerns
    concern_counts = {}
    for label in labels:
        for concern in label.concerns or []:
            concern_counts[concern] = concern_counts.get(concern, 0) + 1
    
    top_concerns = sorted(concern_counts.items(), key=lambda x: x[1], reverse=True)[:3]
    
    # Sentiment mix
    sentiment_counts = {
        "optimistic": 0,
        "neutral": 0,
        "pessimistic": 0,
        "mixed": 0
    }
    
    for label in labels:
        sentiment = label.sentiment or "neutral"
        sentiment_counts[sentiment] = sentiment_counts.get(sentiment, 0) + 1
    
    sentiment_mix = {k: v / total_questions for k, v in sentiment_counts.items()}
    
    # Notable questions (high complexity or unique)
    notable = [
        m.content for m in messages
        if len(m.content.split()) > 15  # Long questions
    ][:5]
    
    # Coverage gaps (questions with low retrieval score)
    low_coverage_messages = db.query(Message).join(RetrievalEvent).filter(
        Message.id.in_(message_ids)
    ).group_by(Message.id).having(
        func.max(RetrievalEvent.score) < 0.5  # Low max score
    ).limit(5).all()
    
    coverage_gaps = [m.content for m in low_coverage_messages]
    
    # Store insights
    insights = DailyInsights(
        corpus_id=corpus_id,
        date=date,
        total_questions=total_questions,
        top_topics=[{"topic": t, "count": c} for t, c in top_topics],
        top_concerns=[{"concern": c, "count": cnt} for c, cnt in top_concerns],
        sentiment_mix=sentiment_mix,
        notable_questions=notable,
        coverage_gaps=coverage_gaps
    )
    db.add(insights)
    db.commit()
    
    print(f"✓ Computed insights for {date}: {total_questions} questions")
```

---

### **Task 8.5: Admin Analytics Endpoints**

**File: `app/api/admin.py`**

```python
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.analytics import DailyInsights, TopicCluster

router = APIRouter()

@router.get("/admin/insights")
def get_insights(
    corpus_id: int,
    start: datetime.date = Query(...),
    end: datetime.date = Query(...),
    db: Session = Depends(get_db)
):
    """Get daily insights for date range"""
    insights = db.query(DailyInsights).filter(
        DailyInsights.corpus_id == corpus_id,
        DailyInsights.date >= start,
        DailyInsights.date <= end
    ).order_by(DailyInsights.date).all()
    
    return {
        "corpus_id": corpus_id,
        "insights": [
            {
                "date": i.date.isoformat(),
                "total_questions": i.total_questions,
                "top_topics": i.top_topics,
                "top_concerns": i.top_concerns,
                "sentiment_mix": i.sentiment_mix,
                "notable_questions": i.notable_questions,
                "coverage_gaps": i.coverage_gaps
            }
            for i in insights
        ]
    }

@router.get("/admin/top_questions")
def get_top_questions(
    corpus_id: int,
    start: datetime.date = Query(...),
    end: datetime.date = Query(...),
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """Get most frequent questions"""
    # Count identical questions
    from sqlalchemy import func
    
    results = db.query(
        Message.content,
        func.count(Message.id).label('count')
    ).join(Conversation).filter(
        Conversation.corpus_id == corpus_id,
        Message.role == "user",
        Message.created_at >= datetime.combine(start, datetime.min.time()),
        Message.created_at < datetime.combine(end, datetime.max.time())
    ).group_by(Message.content).order_by(func.count(Message.id).desc()).limit(limit).all()
    
    return {
        "corpus_id": corpus_id,
        "questions": [
            {"question": r.content, "count": r.count}
            for r in results
        ]
    }
```

---

## ✅ Acceptance Criteria

### **Test 1: Runtime Logging**
```sql
SELECT COUNT(*) FROM retrieval_events WHERE conversation_id = 1;
```
**Expected:** > 0 (events logged with full citation data)

### **Test 2: Message Labeling**
```bash
python -m ingestion.label_messages 1
```
```sql
SELECT sentiment, COUNT(*) FROM message_labels GROUP BY sentiment;
```
**Expected:** Distribution across optimistic/neutral/pessimistic/mixed

### **Test 3: Daily Insights**
```bash
python -m ingestion.daily_rollup 1 2026-01-30
```
```sql
SELECT * FROM daily_insights WHERE date = '2026-01-30';
```
**Expected:** Row with total_questions, top_topics, top_concerns, sentiment_mix, coverage_gaps populated

---

## 📝 Deliverables

- [ ] Runtime logging (retrieval_events with citations)
- [ ] Offline labeling job working
- [ ] Offline clustering job working
- [ ] Daily insights rollup working
- [ ] Admin analytics endpoints working

---

## 🔗 Next Phase

- **Phase 9: Frontend** (summary.html, chat.html with evidence panels)
