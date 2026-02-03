"""
RAG Chat API v2 - Advanced Conversational RAG
Uses multi-query retrieval, deduplication, MMR, and session management
Now with Firebase authentication and Firestore session persistence
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from openai import OpenAI
import os
import logging

from app.services.conversational_rag import conversational_retrieve
from app.services.guardrails import (
    apply_guardrails,
    GuardrailViolation,
    log_security_event,
    get_refusal_message
)
from app.core.firebase_middleware import get_current_user
from app.services.firestore_sessions import firestore_sessions

router = APIRouter()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
logger = logging.getLogger(__name__)


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    question: str
    session_id: str  # Required for session management
    conversation_history: Optional[List[ChatMessage]] = None
    top_k: Optional[int] = 5


class Citation(BaseModel):
    source: str
    document: str
    page: Optional[str] = None
    chapter: Optional[str] = None
    section: Optional[str] = None
    sheet: Optional[str] = None
    score: float


class ChatResponse(BaseModel):
    answer: str
    citations: List[Citation]
    context_used: int
    session_id: str
    turn_number: int


def build_context(chunks: List[dict]) -> str:
    """Build context string from retrieved chunks"""
    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        metadata = chunk.get('metadata', {})
        text = metadata.get('text', '')
        source = metadata.get('corpus_name', 'Unknown')
        doc = metadata.get('document_title', 'Unknown')
        
        context_parts.append(f"[Source {i}: {source} - {doc}]\n{text}\n")
    
    return "\n".join(context_parts)


def build_citations(chunks: List[dict]) -> List[Citation]:
    """Build citation list from chunks"""
    citations = []
    
    for chunk in chunks:
        metadata = chunk.get('metadata', {})
        source_type = metadata.get('source_type', 'unknown')
        
        citation = Citation(
            source=metadata.get('corpus_name', 'Unknown'),
            document=metadata.get('document_title', 'Unknown'),
            score=chunk.get('score', 0.0)
        )
        
        if source_type == 'pdf':
            page_start = metadata.get('page_start')
            page_end = metadata.get('page_end')
            if page_start and page_end:
                citation.page = f"{page_start}-{page_end}"
            citation.chapter = metadata.get('chapter', '')[:100] if metadata.get('chapter') else None
            citation.section = metadata.get('section', '')[:100] if metadata.get('section') else None
        else:
            citation.sheet = metadata.get('sheet_name', 'Unknown')
        
        citations.append(citation)
    
    return citations


def generate_answer(
    question: str,
    context: str,
    conversation_history: Optional[List[dict]] = None
) -> str:
    """Generate answer using OpenAI with RAG context"""
    
    system_prompt = """You are an expert economic analyst specializing in India's Economic Survey and Union Budget 2025-26. You communicate insights in a clear, narrative style - as if explaining to a colleague or client.

Your Communication Style:
- Write in flowing, conversational paragraphs that tell the story behind the data
- Weave numbers and facts naturally into your narrative rather than listing them
- Explain the "why" and "so what" behind statistics, not just the "what"
- Connect different pieces of information to paint a complete picture
- Use transitions to guide the reader through your analysis smoothly
- Be engaging and insightful while remaining factual and grounded

Core Principles:
1. Base ALL answers ONLY on the provided context from official documents
2. Transform data points into narrative explanations
3. Reference sources naturally within your narrative
4. When discussing trends, describe the trajectory and its implications
5. For complex topics, build your explanation step-by-step
6. Avoid bullet points unless absolutely necessary - prefer cohesive paragraphs
7. If information is missing, explain what you can answer and what remains unclear
8. **For follow-up questions**: Focus on NEW information not previously covered. Avoid repeating facts already explained. Build incrementally on the conversation.
9. **For "tell me more" type queries**: Provide deeper analysis, additional angles, or related aspects not yet discussed.

If the question cannot be answered from the context, respond conversationally: "Based on the available documents, I don't have sufficient information to fully address this question."
"""
    
    user_prompt = f"""Context from Economic Survey and Budget documents:

{context}

---

Question: {question}

Provide a narrative, flowing answer that explains this topic clearly and comprehensively. Weave the data and facts into a cohesive story. If this is a follow-up question, focus on adding NEW information rather than repeating what was already discussed."""
    
    # Build messages with conversation history
    messages = [{"role": "system", "content": system_prompt}]
    
    # Add recent conversation history (last 3 exchanges)
    if conversation_history:
        recent_history = conversation_history[-6:]
        messages.extend([{"role": msg["role"], "content": msg["content"]} for msg in recent_history])
    
    messages.append({"role": "user", "content": user_prompt})
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.5,
        max_tokens=1500
    )
    
    return response.choices[0].message.content


@router.post("/rag-chat-v2", response_model=ChatResponse)
async def rag_chat_v2(
    request: ChatRequest,
    user: dict = Depends(get_current_user)
):
    """
    Advanced RAG-powered chat endpoint with Firebase authentication
    
    Features:
    - Firebase authentication (required)
    - Firestore session persistence
    - Multi-query retrieval for better coverage
    - Deduplication to avoid repetition
    - MMR for diverse results
    - Session management for conversation continuity
    - Query expansion using conversation history
    - Multi-layer security guardrails
    """
    try:
        # Extract user info
        user_id = user['uid']
        user_email = user.get('email', 'unknown')
        
        # Input validation
        if not request.question or len(request.question.strip()) == 0:
            raise HTTPException(status_code=400, detail="Question cannot be empty")
        
        if not request.session_id:
            raise HTTPException(status_code=400, detail="session_id is required")
        
        logger.info(f"RAG Chat v2: User {user_email} (session: {request.session_id})")
        
        # SECURITY: Apply guardrails to input query
        try:
            apply_guardrails(
                query=request.question,
                answer=None,  # Pre-generation check
                enable_llm_validation=True  # Use LLM for intent validation
            )
        except GuardrailViolation as e:
            # Log security event
            log_security_event(
                query=request.question,
                violation_type=e.violation_type,
                severity=e.severity,
                session_id=request.session_id
            )
            
            # Return safe refusal message
            refusal_message = get_refusal_message(e.violation_type)
            logger.info(f"Guardrail blocked query: {e.violation_type}")
            
            return ChatResponse(
                answer=refusal_message,
                citations=[],
                context_used=0,
                session_id=request.session_id,
                turn_number=0
            )
        
        # Load session from Firestore (if exists)
        session_data = await firestore_sessions.get_session(
            session_id=request.session_id,
            user_id=user_id
        )
        
        # Use stored conversation history if available, otherwise use request history
        if session_data and 'conversation_history' in session_data:
            history_dicts = session_data['conversation_history']
            logger.info(f"Loaded {len(history_dicts)} messages from Firestore")
        elif request.conversation_history:
            history_dicts = [
                {"role": msg.role, "content": msg.content}
                for msg in request.conversation_history
            ]
            logger.info(f"Using {len(history_dicts)} messages from request")
        else:
            history_dicts = None
            logger.info("Starting new conversation (no history)")
        
        # Conversational retrieval with full pipeline
        chunks, session_state = conversational_retrieve(
            query=request.question,
            session_id=request.session_id,
            conversation_history=history_dicts,
            top_k=request.top_k
        )
        
        if not chunks:
            raise HTTPException(
                status_code=404,
                detail="No relevant information found in the documents"
            )
        
        # Build context and citations
        context = build_context(chunks)
        citations = build_citations(chunks)
        
        # Generate answer with conversation awareness
        answer = generate_answer(request.question, context, history_dicts)
        
        # SECURITY: Validate response safety before returning
        try:
            apply_guardrails(
                query=request.question,
                answer=answer,
                enable_llm_validation=False  # Skip intent check for output
            )
        except GuardrailViolation as e:
            # Log security event
            log_security_event(
                query=request.question,
                violation_type=e.violation_type,
                severity=e.severity,
                session_id=request.session_id
            )
            
            # Return safe fallback message
            refusal_message = get_refusal_message(e.violation_type)
            logger.warning(f"Response blocked by guardrails: {e.violation_type}")
            
            return ChatResponse(
                answer=refusal_message,
                citations=[],
                context_used=0,
                session_id=request.session_id,
                turn_number=session_state.turn_count
            )
        
        # Save updated session to Firestore
        updated_history = history_dicts or []
        updated_history.append({"role": "user", "content": request.question})
        updated_history.append({"role": "assistant", "content": answer})
        
        await firestore_sessions.save_session(
            session_id=request.session_id,
            user_id=user_id,
            conversation_history=updated_history,
            metadata={
                "top_k": request.top_k,
                "chunks_retrieved": len(chunks),
                "user_email": user_email
            }
        )
        logger.info(f"Session {request.session_id} saved to Firestore")
        
        return ChatResponse(
            answer=answer,
            citations=citations,
            context_used=len(chunks),
            session_id=request.session_id,
            turn_number=session_state.turn_count
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing request: {str(e)}"
        )


@router.get("/rag-chat-v2/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "rag-chat-v2",
        "features": [
            "multi-query-retrieval",
            "deduplication",
            "mmr-diversity",
            "session-management",
            "query-expansion"
        ]
    }
