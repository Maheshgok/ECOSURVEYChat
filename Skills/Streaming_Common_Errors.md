# Streaming & SSE Common Errors (Phase 7)

**Reference:** Skills/Chat_API_Streaming_Skills.md

---

## Error 1: EventSource Connection Fails

**Symptom:** Browser console shows "EventSource failed"

**Cause:** CORS not configured for SSE

**Fix:**
```python
# In main.py:
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://your-app.netlify.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## Error 2: Cookies Not Sent with EventSource

**Symptom:** SSE stream fails with 401 Unauthorized

**Cause:** EventSource doesn't send cookies by default in cross-domain

**Fix (Same-domain):**
- Serve frontend from backend OR use same apex domain
- EventSource will include cookies automatically

**Fix (Cross-domain):**
- Use `SameSite=None; Secure` cookies
- EventSource with `withCredentials: true` (limited browser support)
- **OR** use polling fallback for cross-domain

---

## Error 3: SSE Events Not Formatted Correctly

**Symptom:** Frontend receives garbled data

**Cause:** SSE format requires double newline

**Fix:**
```python
def format_sse_event(event_type: str, data: dict) -> str:
    # MUST end with \n\n
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
```

---

## Error 4: Stream Buffers Entire Response

**Symptom:** No incremental streaming, all text appears at once

**Cause:** WSGI server buffering

**Fix:**
```python
# Use ASGI server (Uvicorn) not WSGI (Gunicorn)
# Run with:
uvicorn app.main:app --host 0.0.0.0 --port 8000

# In StreamingResponse, yield frequently:
for chunk in llm_stream:
    yield format_sse_event("token", {"text": chunk})
    # No explicit flush needed with Uvicorn
```

---

## Error 5: Frontend Stops Receiving After 30 Seconds

**Symptom:** EventSource closes after 30s

**Cause:** Load balancer timeout (common on Cloud Run, Netlify proxies)

**Fix:**
```python
# Send keepalive comments every 15 seconds
import asyncio

async def stream_with_keepalive(generator):
    last_event = time.time()
    
    for event in generator:
        yield event
        last_event = time.time()
    
    # Keepalive loop
    while True:
        if time.time() - last_event > 15:
            yield ": keepalive\n\n"  # SSE comment
            last_event = time.time()
        
        await asyncio.sleep(5)
```

---

## Error 6: JSON Parsing Fails in Frontend

**Symptom:** `JSON.parse()` error on event.data

**Cause:** LLM response is not valid JSON

**Fix:**
```python
# In LLM prompt, enforce JSON schema:
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[...],
    response_format={"type": "json_object"},  # ADD THIS
    ...
)

# Validate JSON before sending:
try:
    response_json = json.loads(full_response)
except json.JSONDecodeError:
    yield format_sse_event("error", {"message": "Invalid JSON from LLM"})
    return
```

---

## Error 7: Multiple Conversations Race

**Symptom:** User starts second conversation, first one stops working

**Cause:** Frontend only tracks one EventSource

**Fix:**
```javascript
// Track multiple streams
const activeStreams = new Map();  // conversationId → EventSource

function startChatStream(conversationId) {
    // Close existing stream for this conversation
    if (activeStreams.has(conversationId)) {
        activeStreams.get(conversationId).close();
    }
    
    const eventSource = new EventSource(`/api/chat/stream/${conversationId}`);
    activeStreams.set(conversationId, eventSource);
    
    eventSource.addEventListener('final', () => {
        eventSource.close();
        activeStreams.delete(conversationId);
    });
}
```

---

## Error 8: Partial Message Not Stored

**Symptom:** Page refresh loses streaming message

**Cause:** Message only stored on "final" event

**Fix:**
```javascript
// Store partial message in localStorage
eventSource.addEventListener('token', (event) => {
    const data = JSON.parse(event.data);
    responseBuffer += data.text;
    
    // Persist partial
    localStorage.setItem(`partial_${conversationId}`, responseBuffer);
});

eventSource.addEventListener('final', () => {
    // Clear partial
    localStorage.removeItem(`partial_${conversationId}`);
});

// On page load, restore partial
const partial = localStorage.getItem(`partial_${conversationId}`);
if (partial) {
    document.getElementById('response').textContent = partial + " (resuming...)";
}
```

---

## Error 9: Stream Hangs on Error

**Symptom:** EventSource never receives "error" or "final" event

**Cause:** Exception in stream generator not caught

**Fix:**
```python
async def stream_response(db, conversation_id):
    try:
        # ... streaming logic ...
        
        yield format_sse_event("final", response_json)
        
    except Exception as e:
        # CRITICAL: Always send error event
        yield format_sse_event("error", {"message": str(e)})
    finally:
        # Cleanup
        db.close()
```

---

## Error 10: Browser Tab Closes, Stream Continues

**Symptom:** Server continues processing after user closes tab

**Cause:** No client disconnect detection

**Fix:**
```python
async def stream_response(db, conversation_id):
    try:
        for chunk in llm_stream:
            yield format_sse_event("token", {"text": chunk})
            
            # Check if client disconnected
            # (FastAPI handles this automatically, but be aware)
    except asyncio.CancelledError:
        # Client disconnected
        print(f"Client disconnected from conversation {conversation_id}")
        raise
```

---

## Error 11: LLM Stream Timeout

**Symptom:** EventSource waits forever, no tokens received

**Cause:** LLM API timeout

**Fix:**
```python
import asyncio

async def stream_response(db, conversation_id):
    try:
        # Set timeout
        async with asyncio.timeout(60):  # 60 second timeout
            for chunk in llm_stream:
                yield format_sse_event("token", {"text": chunk})
    
    except asyncio.TimeoutError:
        yield format_sse_event("error", {"message": "LLM timeout"})
```

---

## Error 12: Reconnection Creates Duplicate Messages

**Symptom:** After reconnection, same conversation shows duplicate responses

**Cause:** Reconnection replays stream from beginning

**Fix:**
```javascript
// Track last event ID
let lastEventId = null;

eventSource.addEventListener('token', (event) => {
    lastEventId = event.lastEventId;  // SSE provides this
    // ...
});

// On reconnection, send last event ID
function reconnect() {
    const url = lastEventId 
        ? `/api/chat/stream/${conversationId}?lastEventId=${lastEventId}`
        : `/api/chat/stream/${conversationId}`;
    
    const eventSource = new EventSource(url);
    // ...
}
```

**Backend support:**
```python
@router.get("/chat/stream/{conversation_id}")
async def stream_chat(conversation_id: int, lastEventId: str = None):
    # Resume from lastEventId if provided
    # (requires event ID tracking in DB)
```

---

## Debugging Checklist

- [ ] CORS configured for SSE endpoint
- [ ] Cookies sent with EventSource (same-domain OR cross-domain setup)
- [ ] SSE events formatted with \n\n
- [ ] ASGI server (Uvicorn) used
- [ ] Keepalive comments sent every 15s
- [ ] LLM response validated as JSON
- [ ] Multiple streams tracked properly
- [ ] Partial messages persisted
- [ ] Error events always sent
- [ ] Client disconnect handled
- [ ] LLM timeout configured
- [ ] Reconnection doesn't duplicate

---

## Escalation

If streaming still fails:
1. Test SSE endpoint with `curl -N`
2. Check browser network tab for SSE connection
3. Verify CORS headers in response
4. Test with simple hardcoded stream first
5. Check if load balancer supports SSE
