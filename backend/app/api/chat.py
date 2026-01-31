"""Chat endpoints"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import hashlib
import json
import time

from app.core.database import get_db
from app.core.settings import settings
from app.api.auth import get_current_user_dependency, UserResponse
from app.models import Conversation, Message, ChatSession, User
from app.services.retrieval_service import build_context_pack

router = APIRouter()


class EvidenceItem(BaseModel):
    type: str
    id: str
    label: Optional[str] = None
    name: Optional[str] = None
    topic: Optional[str] = None


class ChatRequest(BaseModel):
    corpus_id: str = Field(..., description="Corpus ID")
    conversation_id: Optional[str] = Field(None, description="Existing conversation ID")
    message: str = Field(..., description="User message")


class ChatResponse(BaseModel):
    conversation_id: str
    answer: str
    intuition: str
    evidence: List[EvidenceItem]
    followups: List[str]


def _user_pseudo_id(google_id: str) -> str:
    salt = settings.SERVER_SALT or ""
    return hashlib.sha256(f"{google_id}{salt}".encode("utf-8")).hexdigest()


def _ensure_conversation(
    db: Session,
    corpus_id: str,
    user: User,
    conversation_id: Optional[str],
) -> Conversation:
    if conversation_id:
        conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        if str(conversation.corpus_id) != str(corpus_id):
            raise HTTPException(status_code=400, detail="Conversation corpus mismatch")
        return conversation

    pseudo_id = _user_pseudo_id(user.google_id)
    chat_session = db.query(ChatSession).filter(ChatSession.user_pseudo_id == pseudo_id).first()
    if not chat_session:
        chat_session = ChatSession(user_pseudo_id=pseudo_id)
        db.add(chat_session)
        db.commit()
        db.refresh(chat_session)

    conversation = Conversation(
        corpus_id=corpus_id,
        chat_session_id=chat_session.id,
        user_id=user.id,
        user_pseudo_id=pseudo_id,
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


def _collect_conversation_memory(db: Session, conversation_id: str) -> List[Dict[str, Any]]:
    messages = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(6)
        .all()
    )
    return [
        {"role": message.role, "content": message.content}
        for message in reversed(messages)
    ]


def _fallback_response(context_pack: Dict) -> Dict[str, Any]:
    claim_cards = context_pack.get("claim_cards", [])
    narrative_nodes = context_pack.get("narrative_nodes", [])
    data_items = context_pack.get("data_items", [])

    answer = "Based on the retrieved evidence, here is a concise summary."
    intuition = "The evidence points to these themes in the survey and datasets."

    if claim_cards:
        answer = claim_cards[0].get("claim_text") or answer
        intuition = claim_cards[0].get("explanation") or intuition
    elif narrative_nodes:
        answer = narrative_nodes[0].get("title") or narrative_nodes[0].get("snippet") or answer
    elif data_items:
        indicator = data_items[0].get("indicator_name")
        answer = f"The latest data highlight {indicator}."

    followups = [
        "Want a breakdown by topic?",
        "Should I pull the most relevant table or series?",
        "Do you want a short interpretation of the drivers?",
    ]

    evidence: List[Dict[str, Any]] = []
    for item in context_pack.get("claim_cards", []):
        evidence.append({"type": "claim_card", "id": item.get("id"), "topic": item.get("topic")})
    for item in context_pack.get("narrative_nodes", []):
        evidence.append({"type": "node", "id": item.get("id"), "label": item.get("label")})
    for item in context_pack.get("data_items", []):
        evidence.append({"type": "series", "id": item.get("id"), "name": item.get("indicator_name")})

    return {
        "answer": answer,
        "intuition": intuition,
        "evidence": evidence,
        "followups": followups,
    }


def _validate_response(payload: Dict[str, Any]) -> bool:
    required = {"answer", "intuition", "evidence", "followups"}
    if not required.issubset(payload.keys()):
        return False
    if not isinstance(payload.get("evidence"), list):
        return False
    if not isinstance(payload.get("followups"), list):
        return False
    return True


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
):
    """Chat endpoint - Phase 7 retrieval + response"""
    # Handle auth based on testing flag
    if settings.SKIP_AUTH_FOR_TESTING:
        # For testing: use test user from database
        user = db.query(User).filter(User.google_id == "test_google_sub").first()
        if not user:
            raise HTTPException(status_code=401, detail="Test user not found")
    else:
        # For production: require authentication
        try:
            # This will call get_current_user_dependency manually
            # which requires the Bearer token from headers
            raise HTTPException(status_code=401, detail="Authentication required")
        except Exception:
            raise HTTPException(status_code=401, detail="Authentication required")

    conversation = _ensure_conversation(db, request.corpus_id, user, request.conversation_id)

    user_message = Message(
        conversation_id=conversation.id,
        role="user",
        content=request.message,
    )
    db.add(user_message)
    db.commit()
    db.refresh(user_message)

    start_time = time.monotonic()
    memory = _collect_conversation_memory(db, str(conversation.id))
    retrieval = build_context_pack(db, request.corpus_id, request.message, memory)

    response_payload = _fallback_response(retrieval.context_pack)
    if not _validate_response(response_payload):
        response_payload = _fallback_response(retrieval.context_pack)

    assistant_message = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=response_payload["answer"],
        message_metadata={
            "intuition": response_payload["intuition"],
            "evidence": response_payload["evidence"],
            "followups": response_payload["followups"],
        },
    )
    db.add(assistant_message)
    db.commit()
    db.refresh(assistant_message)

    latency_ms = int((time.monotonic() - start_time) * 1000)
    from app.models import RetrievalEvent
    retrieval_event = RetrievalEvent(
        conversation_id=conversation.id,
        message_id=assistant_message.id,
        user_id=user.id,
        retrieved_node_ids=retrieval.retrieved_node_ids,
        retrieved_series_ids=retrieval.retrieved_series_ids,
        used_evidence=retrieval.used_evidence,
        latency_ms=latency_ms,
    )
    db.add(retrieval_event)
    db.commit()

    return ChatResponse(
        conversation_id=str(conversation.id),
        answer=response_payload["answer"],
        intuition=response_payload["intuition"],
        evidence=[EvidenceItem(**item) for item in response_payload["evidence"]],
        followups=response_payload["followups"],
    )


@router.get("/chat/stream/{conversation_id}")
async def chat_stream(
    conversation_id: str,
    message: Optional[str] = Query(None),
    corpus_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Chat SSE stream - Phase 7 retrieval + response"""
    # Handle auth based on testing flag
    if settings.SKIP_AUTH_FOR_TESTING:
        # For testing: use test user from database
        user = db.query(User).filter(User.google_id == "test_google_sub").first()
        if not user:
            raise HTTPException(status_code=401, detail="Test user not found")
    else:
        # For production: require authentication
        raise HTTPException(status_code=401, detail="Authentication required")

    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if message:
        user_message = Message(
            conversation_id=conversation.id,
            role="user",
            content=message,
        )
        db.add(user_message)
        db.commit()
        db.refresh(user_message)
        active_message = message
        corpus_id = corpus_id or str(conversation.corpus_id)
    else:
        latest_user = (
            db.query(Message)
            .filter(Message.conversation_id == conversation.id, Message.role == "user")
            .order_by(Message.created_at.desc())
            .first()
        )
        if not latest_user:
            raise HTTPException(status_code=400, detail="No user message to respond to")
        active_message = latest_user.content
        corpus_id = str(conversation.corpus_id)

    memory = _collect_conversation_memory(db, str(conversation.id))
    retrieval = build_context_pack(db, corpus_id, active_message, memory)
    response_payload = _fallback_response(retrieval.context_pack)

    assistant_message = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=response_payload["answer"],
        message_metadata={
            "intuition": response_payload["intuition"],
            "evidence": response_payload["evidence"],
            "followups": response_payload["followups"],
        },
    )
    db.add(assistant_message)
    db.commit()
    db.refresh(assistant_message)

    def event_stream():
        answer = response_payload["answer"]
        for i in range(0, len(answer), 80):
            chunk = answer[i:i + 80]
            yield f"event: chunk\ndata: {chunk}\n\n"
        yield "event: done\n"
        yield f"data: {json.dumps(response_payload)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
