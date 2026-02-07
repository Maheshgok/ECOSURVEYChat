"""
GraphRAG API Endpoints - Fact-based retrieval with explainable reasoning
Separate from regular RAG for structured fact queries
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict
import logging

from app.services.graphrag_retriever import GraphRAGRetriever
from app.services.fact_extractor import FactExtractor
from app.models.fact import RAGIngressFact, FactSearchQuery
from app.core.firebase_middleware import get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)

# Lazy initialization
_retriever = None
_extractor = None


def get_retriever() -> GraphRAGRetriever:
    """Get or create GraphRAG retriever instance"""
    global _retriever
    if _retriever is None:
        _retriever = GraphRAGRetriever(pinecone_index_name="ecosurvey-facts")
    return _retriever


def get_extractor() -> FactExtractor:
    """Get or create fact extractor instance"""
    global _extractor
    if _extractor is None:
        _extractor = FactExtractor()
    return _extractor


class GraphRAGQuery(BaseModel):
    """Request model for fact-based queries"""
    question: str
    top_k: int = 10
    use_graph_traversal: bool = True
    source_filter: Optional[List[str]] = None
    entity_filter: Optional[List[str]] = None
    min_certainty: float = 0.0


class GraphRAGResponse(BaseModel):
    """Response with answer, reasoning, and fact citations"""
    answer: str
    reasoning_steps: List[str]
    supporting_facts: List[Dict]
    confidence: float
    caveats: Optional[List[str]] = None
    graph_traversal_used: bool


class FactIngestionRequest(BaseModel):
    """Request to ingest and extract facts from text"""
    text: str
    source_origin: str
    page_reference: int
    document_id: Optional[str] = None


@router.post("/graphrag/query", response_model=GraphRAGResponse)
async def query_graphrag(
    request: GraphRAGQuery,
    user: Dict = Depends(get_current_user)
):
    """
    Query the knowledge graph using structured facts
    
    Returns:
        - Explicit reasoning chain
        - Fact citations with certainty scores
        - Graph traversal path (if enabled)
        - Confidence score
    """
    try:
        logger.info(f"GraphRAG query from user {user['uid']}: {request.question[:50]}...")
        
        retriever = get_retriever()
        
        # Build filters
        filters = {}
        if request.source_filter:
            filters['source_origin'] = request.source_filter
        if request.entity_filter:
            filters['entities'] = request.entity_filter
        if request.min_certainty > 0:
            filters['min_certainty'] = request.min_certainty
        
        # Get answer with reasoning
        result = retriever.answer_with_reasoning(
            query=request.question,
            top_k=request.top_k,
            use_graph=request.use_graph_traversal
        )
        
        return GraphRAGResponse(
            answer=result['answer'],
            reasoning_steps=result['reasoning_steps'],
            supporting_facts=result['supporting_facts'],
            confidence=result['confidence'],
            caveats=result.get('caveats'),
            graph_traversal_used=request.use_graph_traversal
        )
        
    except Exception as e:
        logger.error(f"GraphRAG query error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/graphrag/extract-facts", response_model=List[RAGIngressFact])
async def extract_facts(
    request: FactIngestionRequest,
    user: Dict = Depends(get_current_user)
):
    """
    Extract structured facts from raw text
    
    Useful for testing fact extraction before full ingestion
    """
    try:
        logger.info(f"Fact extraction request from user {user['uid']}")
        
        extractor = get_extractor()
        
        facts = extractor.extract_facts(
            chunk_text=request.text,
            source_origin=request.source_origin,
            page_reference=request.page_reference,
            document_id=request.document_id
        )
        
        return facts
        
    except Exception as e:
        logger.error(f"Fact extraction error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/graphrag/facts/{fact_id}")
async def get_fact(
    fact_id: str,
    user: Dict = Depends(get_current_user)
):
    """Retrieve a specific fact by ID"""
    try:
        retriever = get_retriever()
        fact = retriever._fetch_fact_by_id(fact_id)
        
        if not fact:
            raise HTTPException(status_code=404, detail="Fact not found")
        
        return fact
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Fact retrieval error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/graphrag/search-facts")
async def search_facts(
    query: FactSearchQuery,
    user: Dict = Depends(get_current_user)
):
    """
    Search facts with advanced filters
    
    Filters:
        - subject_filter: Filter by fact subjects
        - entity_filter: Filter by related entities
        - temporal_filter: Filter by time period
        - source_filter: Filter by document source
        - min_certainty: Minimum certainty score
        - sentiment_range: Filter by sentiment magnitude
    """
    try:
        retriever = get_retriever()
        
        # Build Pinecone metadata filter
        filters = {}
        if query.source_filter:
            filters['source_origin'] = query.source_filter
        if query.min_certainty > 0:
            filters['min_certainty'] = query.min_certainty
        
        facts = retriever.retrieve_facts(
            query=query.query_text,
            top_k=query.top_k,
            filters=filters
        )
        
        # Apply additional filters (Pinecone doesn't support all filter types)
        if query.subject_filter:
            facts = [f for f in facts if f.subject in query.subject_filter]
        
        if query.entity_filter:
            facts = [
                f for f in facts 
                if any(entity in f.related_entities for entity in query.entity_filter)
            ]
        
        if query.temporal_filter:
            facts = [f for f in facts if f.temporal_context == query.temporal_filter]
        
        if query.sentiment_range:
            min_sent, max_sent = query.sentiment_range
            facts = [
                f for f in facts 
                if min_sent <= f.sentiment_magnitude <= max_sent
            ]
        
        return {"facts": facts, "count": len(facts)}
        
    except Exception as e:
        logger.error(f"Fact search error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/graphrag/stats")
async def get_stats(user: Dict = Depends(get_current_user)):
    """Get statistics about the fact knowledge base"""
    try:
        retriever = get_retriever()
        
        # Get index stats from Pinecone
        stats = retriever.index.describe_index_stats()
        
        return {
            "total_facts": stats.get('total_vector_count', 0),
            "index_fullness": stats.get('index_fullness', 0.0),
            "dimensions": stats.get('dimension', 3072),
            "namespaces": stats.get('namespaces', {})
        }
        
    except Exception as e:
        logger.error(f"Stats retrieval error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
