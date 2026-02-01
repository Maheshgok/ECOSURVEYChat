"""
Phase 6 API Endpoints - Topic Briefs and Claim Cards
Provides endpoints for retrieving precomputed summaries and claim cards
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.models import TopicBrief, ClaimCard, Corpus
from app.api.auth import get_current_user_dependency as get_current_user, UserResponse


router = APIRouter(prefix="/api/summaries", tags=["summaries"])


# ============================================================================
# Request/Response Models
# ============================================================================

class KeyNumber(BaseModel):
    """Key statistic with citation"""
    value: str
    label: str
    unit: Optional[str] = None
    citation: Optional[str] = None


class TopicBriefResponse(BaseModel):
    """Response model for topic brief"""
    id: str
    corpus_id: str
    topic: str
    bullets: List[str]
    key_numbers: List[KeyNumber]
    linked_node_ids: List[str]
    linked_series_ids: List[str]
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True


class ClaimCardResponse(BaseModel):
    """Response model for claim card"""
    id: str
    corpus_id: str
    topic: str
    claim_text: str
    explanation: Optional[str]
    evidence_node_ids: List[str]
    evidence_series_ids: List[str]
    confidence: float
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True


class TopicBriefListResponse(BaseModel):
    """List of topic briefs"""
    briefs: List[TopicBriefResponse]
    count: int


class ClaimCardListResponse(BaseModel):
    """List of claim cards"""
    claims: List[ClaimCardResponse]
    count: int


class TopicSummary(BaseModel):
    """Summary statistics for topics"""
    topic: str
    claim_count: int


# ============================================================================
# Topic Brief Endpoints
# ============================================================================

@router.get("/briefs/{corpus_id}", response_model=TopicBriefListResponse)
async def get_topic_briefs(
    corpus_id: UUID,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get all topic briefs for a corpus.
    Returns precomputed summary bullets and key numbers for each topic.
    """
    # Verify corpus exists
    corpus = db.query(Corpus).filter(Corpus.id == corpus_id).first()
    if not corpus:
        raise HTTPException(status_code=404, detail="Corpus not found")
    
    # Get all topic briefs
    briefs = db.query(TopicBrief).filter(
        TopicBrief.corpus_id == corpus_id
    ).order_by(TopicBrief.topic).all()
    
    return TopicBriefListResponse(
        briefs=[
            TopicBriefResponse(
                id=str(brief.id),
                corpus_id=str(brief.corpus_id),
                topic=brief.topic,
                bullets=brief.bullets or [],
                key_numbers=[KeyNumber(**kn) for kn in (brief.key_numbers or [])],
                linked_node_ids=[str(nid) for nid in (brief.linked_node_ids or [])],
                linked_series_ids=[str(sid) for sid in (brief.linked_series_ids or [])],
                created_at=brief.created_at.isoformat(),
                updated_at=brief.updated_at.isoformat()
            )
            for brief in briefs
        ],
        count=len(briefs)
    )


@router.get("/briefs/{corpus_id}/{topic}", response_model=TopicBriefResponse)
async def get_topic_brief_by_topic(
    corpus_id: UUID,
    topic: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get topic brief for a specific topic.
    """
    brief = db.query(TopicBrief).filter(
        TopicBrief.corpus_id == corpus_id,
        TopicBrief.topic == topic
    ).first()
    
    if not brief:
        raise HTTPException(
            status_code=404,
            detail=f"Topic brief not found for topic '{topic}'"
        )
    
    return TopicBriefResponse(
        id=str(brief.id),
        corpus_id=str(brief.corpus_id),
        topic=brief.topic,
        bullets=brief.bullets or [],
        key_numbers=[KeyNumber(**kn) for kn in (brief.key_numbers or [])],
        linked_node_ids=[str(nid) for nid in (brief.linked_node_ids or [])],
        linked_series_ids=[str(sid) for sid in (brief.linked_series_ids or [])],
        created_at=brief.created_at.isoformat(),
        updated_at=brief.updated_at.isoformat()
    )


# ============================================================================
# Claim Card Endpoints
# ============================================================================

@router.get("/claims/{corpus_id}", response_model=ClaimCardListResponse)
async def get_claim_cards(
    corpus_id: UUID,
    topic: Optional[str] = Query(None, description="Filter by topic"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get claim cards for a corpus, optionally filtered by topic.
    Returns atomic claims with explanations and evidence citations.
    """
    # Verify corpus exists
    corpus = db.query(Corpus).filter(Corpus.id == corpus_id).first()
    if not corpus:
        raise HTTPException(status_code=404, detail="Corpus not found")
    
    # Build query
    query = db.query(ClaimCard).filter(ClaimCard.corpus_id == corpus_id)
    
    if topic:
        query = query.filter(ClaimCard.topic == topic)
    
    # Get total count
    total_count = query.count()
    
    # Apply ordering, pagination
    claims = query.order_by(
        ClaimCard.confidence.desc(),
        ClaimCard.created_at.desc()
    ).limit(limit).offset(offset).all()
    
    return ClaimCardListResponse(
        claims=[
            ClaimCardResponse(
                id=str(claim.id),
                corpus_id=str(claim.corpus_id),
                topic=claim.topic,
                claim_text=claim.claim_text,
                explanation=claim.explanation,
                evidence_node_ids=[str(nid) for nid in (claim.evidence_node_ids or [])],
                evidence_series_ids=[str(sid) for sid in (claim.evidence_series_ids or [])],
                confidence=claim.confidence,
                created_at=claim.created_at.isoformat(),
                updated_at=claim.updated_at.isoformat()
            )
            for claim in claims
        ],
        count=total_count
    )


@router.get("/claims/{corpus_id}/search", response_model=ClaimCardListResponse)
async def search_claim_cards(
    corpus_id: UUID,
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Search claim cards by text (claim, explanation, or topic).
    """
    # Verify corpus exists
    corpus = db.query(Corpus).filter(Corpus.id == corpus_id).first()
    if not corpus:
        raise HTTPException(status_code=404, detail="Corpus not found")
    
    # Search across claim_text, explanation, and topic
    search_term = f"%{q}%"
    claims = db.query(ClaimCard).filter(
        ClaimCard.corpus_id == corpus_id,
        (
            ClaimCard.claim_text.ilike(search_term) |
            ClaimCard.explanation.ilike(search_term) |
            ClaimCard.topic.ilike(search_term)
        )
    ).order_by(
        ClaimCard.confidence.desc(),
        ClaimCard.created_at.desc()
    ).limit(limit).all()
    
    return ClaimCardListResponse(
        claims=[
            ClaimCardResponse(
                id=str(claim.id),
                corpus_id=str(claim.corpus_id),
                topic=claim.topic,
                claim_text=claim.claim_text,
                explanation=claim.explanation,
                evidence_node_ids=[str(nid) for nid in (claim.evidence_node_ids or [])],
                evidence_series_ids=[str(sid) for sid in (claim.evidence_series_ids or [])],
                confidence=claim.confidence,
                created_at=claim.created_at.isoformat(),
                updated_at=claim.updated_at.isoformat()
            )
            for claim in claims
        ],
        count=len(claims)
    )


@router.get("/claims/{corpus_id}/{claim_id}", response_model=ClaimCardResponse)
async def get_claim_card(
    corpus_id: UUID,
    claim_id: UUID,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get a specific claim card by ID.
    """
    claim = db.query(ClaimCard).filter(
        ClaimCard.corpus_id == corpus_id,
        ClaimCard.id == claim_id
    ).first()
    
    if not claim:
        raise HTTPException(status_code=404, detail="Claim card not found")
    
    return ClaimCardResponse(
        id=str(claim.id),
        corpus_id=str(claim.corpus_id),
        topic=claim.topic,
        claim_text=claim.claim_text,
        explanation=claim.explanation,
        evidence_node_ids=[str(nid) for nid in (claim.evidence_node_ids or [])],
        evidence_series_ids=[str(sid) for sid in (claim.evidence_series_ids or [])],
        confidence=claim.confidence,
        created_at=claim.created_at.isoformat(),
        updated_at=claim.updated_at.isoformat()
    )


# ============================================================================
# Topic Statistics
# ============================================================================

@router.get("/topics/{corpus_id}", response_model=List[TopicSummary])
async def get_topic_statistics(
    corpus_id: UUID,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get claim card counts by topic for a corpus.
    """
    # Verify corpus exists
    corpus = db.query(Corpus).filter(Corpus.id == corpus_id).first()
    if not corpus:
        raise HTTPException(status_code=404, detail="Corpus not found")
    
    # Get topic counts
    topic_counts = db.query(
        ClaimCard.topic,
        func.count(ClaimCard.id).label('claim_count')
    ).filter(
        ClaimCard.corpus_id == corpus_id
    ).group_by(ClaimCard.topic).order_by(
        func.count(ClaimCard.id).desc()
    ).all()
    
    return [
        TopicSummary(topic=topic, claim_count=count)
        for topic, count in topic_counts
    ]
