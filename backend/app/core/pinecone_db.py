"""
Pinecone configuration for vector storage
"""

import os
from pinecone import Pinecone, ServerlessSpec
from typing import Optional

# Global Pinecone client and index
_pc: Optional[Pinecone] = None
_index = None


def init_pinecone():
    """Initialize Pinecone client"""
    global _pc, _index
    
    if _pc is not None:
        return _pc, _index
    
    api_key = os.getenv("PINECONE_API_KEY")
    if not api_key:
        raise ValueError("PINECONE_API_KEY not set in environment")
    
    index_name = os.getenv("PINECONE_INDEX_NAME", "economic-survey-2026")
    
    # Initialize Pinecone
    _pc = Pinecone(api_key=api_key)
    
    # Connect to index
    _index = _pc.Index(index_name)
    
    return _pc, _index


def get_pinecone_index():
    """Get Pinecone index"""
    global _pc, _index
    
    if _index is None:
        _, _index = init_pinecone()
    
    return _index


def upsert_vectors(vectors: list[dict], batch_size: int = 100):
    """
    Upsert vectors to Pinecone in batches
    
    Args:
        vectors: List of dicts with keys:
            - id: unique ID (string)
            - values: embedding vector (list of floats)
            - metadata: dict with corpus_id, document_id, etc.
        batch_size: Number of vectors per batch (default 100)
    """
    index = get_pinecone_index()
    
    # Upsert in batches to avoid size limits
    for i in range(0, len(vectors), batch_size):
        batch = vectors[i:i + batch_size]
        index.upsert(vectors=batch)


def query_vectors(query_embedding: list[float], top_k: int = 10, filter: dict = None):
    """
    Query Pinecone for similar vectors
    
    Args:
        query_embedding: Query vector
        top_k: Number of results to return
        filter: Metadata filter (e.g., {"corpus_id": "abc123"})
    
    Returns:
        List of matches with id, score, metadata
    """
    index = get_pinecone_index()
    results = index.query(
        vector=query_embedding,
        top_k=top_k,
        filter=filter,
        include_metadata=True
    )
    return results.matches


def delete_vectors(ids: list[str]):
    """Delete vectors by IDs"""
    index = get_pinecone_index()
    index.delete(ids=ids)


def delete_by_filter(filter: dict):
    """Delete vectors by metadata filter"""
    index = get_pinecone_index()
    index.delete(filter=filter)
