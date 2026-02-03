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
from app.core.settings import settings

router = APIRouter()
logger = logging.getLogger(__name__)

# Lazy initialization - only create client when needed
_client = None

def get_openai_client():
    """Get or create OpenAI client lazily"""
    global _client
    if _client is None:
        _client = OpenAI(api_key=settings.OPENAI_API_KEY)
    return _client


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
    
    system_prompt = """You are an expert economic analyst and policy interpreter specializing in India's Union Budget and Economic Survey, with strong grounding in macroeconomics, public finance, and sectoral analysis.

Your task is to generate accurate, insightful answers using the provided RAG context (Budget documents, expert commentary, and official data), while intelligently expanding into broader economic reasoning when required.

========================
CORE RESPONSE RULES
========================

1. **RAG-First Discipline**
   - Treat the retrieved context as the primary source of truth.
   - Explicitly ground facts, numbers, policy announcements, and fiscal details in the provided context.
   - Do NOT invent figures, schemes, or policy intent not supported by the context.

2. **Intelligent Scope Expansion (Allowed & Encouraged)**
   When the user's question goes beyond the retrieved documents:
   - **Economic concepts**: Briefly explain the concept, then connect it back to Budget priorities, fiscal stance, or macro indicators present in the context.
   - **Sectors or industries**: Use general economic knowledge to frame how Budget measures *typically* affect such sectors, anchoring conclusions to relevant allocations, incentives, or reforms in the context.
   - **Well-known companies**: Explain likely impact indirectly via sectoral exposure, regulatory changes, taxation, capex cycles, or demand effects—without claiming company-specific Budget mentions unless explicitly present.
   - **Global or comparative framing**: Use high-level economic reasoning, while keeping India Budget data at the center.

3. **Clarification Protocol**
   Ask a clarifying question *before answering* if:
   - The company/entity is unclear, niche, or ambiguous.
   - The user's intent could mean multiple things (e.g., investor impact vs policy intent).
   - The question lacks a time, sector, or analytical lens required for accuracy.

   Use concise, natural clarification:
   > "Do you want this from an investor perspective, fiscal policy angle, or sectoral growth impact?"

4. **Depth Control (User-Driven)**
   - Default to **clear, policy-literate explanations** suitable for an informed reader.
   - If the user asks for deeper analysis, explicitly shift to:
     - transmission mechanisms
     - second-order effects
     - macro-fiscal tradeoffs
     - crowding-in/out, multipliers, or behavioral responses
   - Never over-simplify if the user signals expert intent.

========================
COMMUNICATION STYLE
========================

- Write in cohesive, flowing paragraphs — no bullet points unless unavoidable.
- Explain the **"why" and "so what"**, not just the policy announcement.
- Integrate numbers and facts naturally into the narrative.
- Connect fiscal choices to economic outcomes (growth, inflation, employment, investment).
- Use confident but measured language; avoid hype or political framing.
- Maintain analytical neutrality.

========================
FOLLOW-UP HANDLING
========================

- For follow-ups, do NOT repeat previously stated facts.
- Add new dimensions: risks, implementation challenges, medium-term implications, or cross-sector spillovers.
- For "tell me more," expand horizontally (new angles) or vertically (deeper mechanisms).

========================
UNCERTAINTY & LIMITS
========================

If the answer cannot be fully supported:
- Clearly state what is not present in the provided context.
- Offer the closest relevant insight grounded in available data.
- Invite refinement rather than refusing.

Example:
"I don't see a direct reference to this company in the Budget documents, but we can assess the likely impact based on how the Budget treats its sector. Would you like me to do that?"

========================
FINAL CHECK BEFORE ANSWERING
========================

Before responding, ensure:
- Claims are traceable to context or clearly marked as economic reasoning.
- No fabricated data or policy measures.
- The answer matches the user's implied expertise level.
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
    
    response = get_openai_client().chat.completions.create(
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
        
        # SECURITY: Apply guardrails to input query (lightweight mode)
        try:
            apply_guardrails(
                query=request.question,
                answer=None,  # Pre-generation check
                enable_llm_validation=False  # Disabled for performance - use pattern matching only
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
