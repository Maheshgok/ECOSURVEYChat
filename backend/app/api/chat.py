"""Chat endpoints - simplified"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid

from app.core.database import get_db
from app.core.settings import settings
from app.api.auth import get_current_user_dependency, UserResponse
from app.models import Message, User, Corpus, Chunk

router = APIRouter()


class ChatRequest(BaseModel):
    message: str = Field(..., description="User message")
    corpus_ids: Optional[List[str]] = Field(None, description="Corpus IDs to search (defaults to ALL)")


class ChatResponse(BaseModel):
    answer: str
    sources: List[str] = []
    corpuses_searched: List[str] = []  # Show which corpuses were queried


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user_dependency) if settings.ENVIRONMENT == "production" else None
):
    """Simple RAG chat endpoint - searches ALL corpuses by default"""
    
    # Get corpuses to search
    if request.corpus_ids:
        # User specified which corpuses to search
        corpuses = db.query(Corpus).filter(Corpus.id.in_([uuid.UUID(cid) for cid in request.corpus_ids])).all()
        if not corpuses:
            raise HTTPException(status_code=404, detail="No corpuses found")
    else:
        # Default: search ALL corpuses
        corpuses = db.query(Corpus).all()
        if not corpuses:
            raise HTTPException(status_code=404, detail="No corpuses available")
    
    corpus_ids = [c.id for c in corpuses]
    corpus_names = [c.name for c in corpuses]
    
    # Get or create dev user (skip auth in development)
    if current_user:
        user = db.query(User).filter(User.google_id == current_user.google_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
    else:
        # Dev mode: use/create test user
        user = db.query(User).filter(User.email == "dev@test.com").first()
        if not user:
            user = User(
                id=uuid.uuid4(),
                google_id="dev_user",
                email="dev@test.com",
                name="Dev User"
            )
            db.add(user)
            db.commit()
    
    # Save user message (use first corpus for message history)
    user_msg = Message(
        user_id=user.id,
        corpus_id=corpus_ids[0],
        role="user",
        content=request.message,
        meta={"corpus_ids": [str(cid) for cid in corpus_ids]}
    )
    db.add(user_msg)
    db.commit()
    
    # Check if we have any chunks with embeddings across ALL selected corpuses
    chunk_count = db.query(Chunk).filter(
        Chunk.corpus_id.in_(corpus_ids),
        Chunk.embedding.isnot(None)
    ).count()
    
    if chunk_count == 0:
        answer = "I don't have any relevant information in my knowledge base to answer that question. Please ensure documents have been uploaded and processed."
        sources = []
    else:
        # TODO: Implement actual RAG retrieval when embeddings are ready
        # For now, return placeholder response
        corpora_str = ", ".join(corpus_names)
        answer = f"I found {chunk_count} document chunks across {len(corpuses)} corpus(es): {corpora_str}. Full RAG retrieval with semantic search is not yet implemented. This will search through all documents and provide relevant answers with citations."
        sources = []
    
    # Save assistant message
    assistant_msg = Message(
        user_id=user.id,
        corpus_id=corpus_ids[0],
        role="assistant",
        content=answer,
        meta={"sources": sources, "corpus_ids": [str(cid) for cid in corpus_ids]}
    )
    db.add(assistant_msg)
    db.commit()
    
    return ChatResponse(
        answer=answer,
        sources=sources,
        corpuses_searched=corpus_names
    )
