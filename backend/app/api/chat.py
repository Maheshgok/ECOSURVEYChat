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
    corpus_id: Optional[str] = Field(None, description="Corpus ID (defaults to first corpus)")


class ChatResponse(BaseModel):
    answer: str
    sources: List[str] = []


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user_dependency)
):
    """Simple RAG chat endpoint"""
    
    # Get corpus
    if request.corpus_id:
        corpus = db.query(Corpus).filter(Corpus.id == uuid.UUID(request.corpus_id)).first()
        if not corpus:
            raise HTTPException(status_code=404, detail="Corpus not found")
    else:
        corpus = db.query(Corpus).first()
        if not corpus:
            raise HTTPException(status_code=404, detail="No corpus available")
    
    # Get user
    user = db.query(User).filter(User.google_id == current_user.google_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Save user message
    user_msg = Message(
        user_id=user.id,
        corpus_id=corpus.id,
        role="user",
        content=request.message,
        meta={}
    )
    db.add(user_msg)
    db.commit()
    
    # Check if we have any chunks with embeddings
    chunk_count = db.query(Chunk).filter(
        Chunk.corpus_id == corpus.id,
        Chunk.embedding.isnot(None)
    ).count()
    
    if chunk_count == 0:
        answer = "I don't have any relevant information in my knowledge base to answer that question. Please ensure documents have been uploaded and processed."
        sources = []
    else:
        # TODO: Implement actual RAG retrieval when embeddings are ready
        # For now, return placeholder response
        answer = f"I found {chunk_count} document chunks in the {corpus.name} corpus, but full RAG retrieval is not yet implemented. This will search through the documents and provide relevant answers with citations."
        sources = []
    
    # Save assistant message
    assistant_msg = Message(
        user_id=user.id,
        corpus_id=corpus.id,
        role="assistant",
        content=answer,
        meta={"sources": sources}
    )
    db.add(assistant_msg)
    db.commit()
    
    return ChatResponse(answer=answer, sources=sources)
