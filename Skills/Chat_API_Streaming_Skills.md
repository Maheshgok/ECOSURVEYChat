# Chat API & Streaming Skills (Phase 7 - Part 2)

**Goal:** Implement Server-Sent Events (SSE) for streaming chat responses

---

## 📋 Prerequisites

- Phase 7 (Part 1): Retrieval & Context Pack completed
- FastAPI SSE understanding
- Frontend EventSource API knowledge

---

## 🎯 Tasks Breakdown

### **Task 7S.1: Chat API Endpoints**

**File: `app/api/chat.py`**

```python
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.chat_service import create_conversation, stream_response

router = APIRouter()

@router.post("/chat")
def create_chat(
    request: dict,
    db: Session = Depends(get_db)
):
    """
    Create new conversation.
    
    Request:
    {
        "corpus_id": 1,
        "question": "What is GDP growth?"
    }
    
    Returns:
    {
        "conversation_id": 123,
        "stream_url": "/api/chat/stream/123"
    }
    """
    corpus_id = request.get("corpus_id")
    question = request.get("question")
    
    if not corpus_id or not question:
        raise HTTPException(status_code=400, detail="Missing corpus_id or question")
    
    # Create conversation
    conversation_id = create_conversation(db, corpus_id, question)
    
    return {
        "conversation_id": conversation_id,
        "stream_url": f"/api/chat/stream/{conversation_id}"
    }

@router.get("/chat/stream/{conversation_id}")
async def stream_chat(
    conversation_id: int,
    db: Session = Depends(get_db)
):
    """
    Stream chat response using Server-Sent Events (SSE).
    
    Events:
    - token: {"text": "..."}
    - final: {"answer": "...", "intuition": "...", "evidence": [...]}
    - error: {"message": "..."}
    """
    return StreamingResponse(
        stream_response(db, conversation_id),
        media_type="text/event-stream"
    )
```

---

### **Task 7S.2: SSE Stream Generator**

**File: `app/services/chat_service.py`**

```python
import json
from typing import AsyncGenerator
from openai import OpenAI

async def stream_response(db: Session, conversation_id: int) -> AsyncGenerator[str, None]:
    """
    Generate SSE stream for chat response.
    
    SSE format:
    event: token
    data: {"text": "GDP"}
    
    event: final
    data: {"answer": "...", "intuition": "...", "evidence": [...]}
    """
    try:
        # Get conversation
        conversation = db.query(Conversation).get(conversation_id)
        if not conversation:
            yield format_sse_event("error", {"message": "Conversation not found"})
            return
        
        # Get question
        messages = db.query(Message).filter(
            Message.conversation_id == conversation_id
        ).order_by(Message.created_at).all()
        
        question = messages[0].content
        
        # Retrieve evidence
        from app.services.retrieval import retrieve_evidence, classify_query
        from app.services.context_pack import assemble_context_pack
        
        query_type = classify_query(question)
        evidence = retrieve_evidence(db, conversation.corpus_id, question, query_type)
        
        # Assemble context pack
        conv_history = [{"role": m.role, "content": m.content} for m in messages[:-1]]
        context_pack = assemble_context_pack(
            db,
            conversation.corpus_id,
            question,
            conv_history,
            evidence
        )
        
        # Build prompt
        prompt = build_practitioner_prompt(question, context_pack)
        
        # Stream from LLM
        client = OpenAI()
        
        stream = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an economic policy expert."},
                {"role": "user", "content": prompt}
            ],
            stream=True,
            temperature=0.3
        )
        
        full_response = ""
        
        for chunk in stream:
            if chunk.choices[0].delta.content:
                token = chunk.choices[0].delta.content
                full_response += token
                
                # Stream token
                yield format_sse_event("token", {"text": token})
        
        # Parse final response
        response_json = json.loads(full_response)
        
        # Validate response
        from app.services.validation import validate_response
        if not validate_response(response_json):
            yield format_sse_event("error", {"message": "STOP: Uncited numeric claim"})
            return
        
        # Store message
        assistant_message = Message(
            conversation_id=conversation_id,
            role="assistant",
            content=json.dumps(response_json)
        )
        db.add(assistant_message)
        db.commit()
        
        # Send final event
        yield format_sse_event("final", response_json)
        
    except Exception as e:
        yield format_sse_event("error", {"message": str(e)})

def format_sse_event(event_type: str, data: dict) -> str:
    """Format SSE event"""
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"

def build_practitioner_prompt(question: str, context_pack: Dict) -> str:
    """Build prompt with context pack"""
    return f"""Answer this question as an economic policy expert.

Question: {question}

Context:
{context_pack['conversation']}

Claims/Briefs:
{context_pack['claims']}

Narrative Evidence:
{context_pack['narrative']}

Data:
{context_pack['data']}

Respond in JSON:
{{
    "answer": "Direct answer (2-3 sentences)",
    "intuition": "Why/how (3-4 sentences)",
    "evidence": [
        {{"node_id": 123, "snippet": "...", "citation": "Section I.2"}},
        {{"table_id": 45, "title": "Table I.1", "relevant_data": "GDP: 7.2%"}}
    ],
    "followups": ["Question 1?", "Question 2?"]
}}

CRITICAL: Cite ALL numeric claims with evidence."""
```

---

### **Task 7S.3: Frontend EventSource**

**File: `frontend/js/chat.js`**

```javascript
function startChatStream(conversationId) {
    const eventSource = new EventSource(`/api/chat/stream/${conversationId}`);
    
    let responseBuffer = '';
    
    eventSource.addEventListener('token', (event) => {
        const data = JSON.parse(event.data);
        responseBuffer += data.text;
        
        // Update UI with streaming text
        document.getElementById('response').textContent = responseBuffer;
    });
    
    eventSource.addEventListener('final', (event) => {
        const response = JSON.parse(event.data);
        
        // Display structured response
        displayAnswer(response.answer);
        displayIntuition(response.intuition);
        displayEvidence(response.evidence);
        displayFollowups(response.followups);
        
        eventSource.close();
    });
    
    eventSource.addEventListener('error', (event) => {
        const error = JSON.parse(event.data);
        console.error('Stream error:', error.message);
        
        document.getElementById('error').textContent = error.message;
        eventSource.close();
    });
    
    eventSource.onerror = () => {
        console.error('EventSource connection failed');
        eventSource.close();
    };
}
```

---

### **Task 7S.4: Reconnection Logic**

**File: `frontend/js/chat.js`**

```javascript
function startChatStreamWithRetry(conversationId, maxRetries = 3) {
    let retries = 0;
    
    function connect() {
        const eventSource = new EventSource(`/api/chat/stream/${conversationId}`);
        
        // ... (same event handlers)
        
        eventSource.onerror = () => {
            eventSource.close();
            
            if (retries < maxRetries) {
                retries++;
                console.log(`Reconnecting... (${retries}/${maxRetries})`);
                setTimeout(connect, 1000 * retries);  // Exponential backoff
            } else {
                console.error('Max retries reached');
                document.getElementById('error').textContent = 'Connection failed';
            }
        };
    }
    
    connect();
}
```

---

## ✅ Acceptance Criteria

### **Test 1: SSE Stream**
```bash
curl -N http://localhost:8000/api/chat/stream/1
```

**Expected:**
```
event: token
data: {"text": "GDP"}

event: token
data: {"text": " growth"}

event: final
data: {"answer": "...", ...}
```

### **Test 2: Frontend Integration**
Open browser console and verify:
- Tokens appear incrementally
- Final response structured correctly
- Evidence panel populates
- Reconnection works after network interrupt

---

## 📝 Deliverables

- [ ] Chat POST endpoint working
- [ ] SSE streaming endpoint working
- [ ] Frontend EventSource implemented
- [ ] Reconnection logic working
- [ ] Response validation enforced

---

## 🔗 Next Phase

- **Phase 8: Analytics & Labeling** (usage tracking, sentiment analysis)
