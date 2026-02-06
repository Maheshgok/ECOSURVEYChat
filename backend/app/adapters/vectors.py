"""
Vector Database Adapter Interface
Abstracts vector stores (Pinecone, Azure AI Search, Weaviate, etc.)
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional
import os
import logging

logger = logging.getLogger(__name__)


class VectorAdapter(ABC):
    """Base interface for vector databases"""
    
    @abstractmethod
    def query(
        self,
        vector: List[float],
        top_k: int = 5,
        filter: Optional[Dict] = None
    ) -> List[Dict]:
        """Query for similar vectors"""
        pass
    
    @abstractmethod
    def upsert(self, vectors: List[Dict]) -> bool:
        """Insert or update vectors"""
        pass
    
    @abstractmethod
    def delete(self, ids: List[str]) -> bool:
        """Delete vectors by ID"""
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """Return provider name for logging/metrics"""
        pass


class PineconeVectorAdapter(VectorAdapter):
    """Pinecone vector database (works on all clouds)"""
    
    def __init__(self):
        from app.core.pinecone_db import get_pinecone_index
        self.get_index = get_pinecone_index
    
    def query(
        self,
        vector: List[float],
        top_k: int = 5,
        filter: Optional[Dict] = None
    ) -> List[Dict]:
        try:
            index = self.get_index()
            results = index.query(
                vector=vector,
                top_k=top_k,
                filter=filter,
                include_metadata=True,
                include_values=True
            )
            
            return [{
                'id': match['id'],
                'score': match['score'],
                'metadata': match.get('metadata', {}),
                'values': match.get('values', [])
            } for match in results.get('matches', [])]
            
        except Exception as e:
            logger.error(f"Pinecone query error: {e}")
            return []
    
    def upsert(self, vectors: List[Dict]) -> bool:
        try:
            index = self.get_index()
            index.upsert(vectors=vectors)
            return True
        except Exception as e:
            logger.error(f"Pinecone upsert error: {e}")
            return False
    
    def delete(self, ids: List[str]) -> bool:
        try:
            index = self.get_index()
            index.delete(ids=ids)
            return True
        except Exception as e:
            logger.error(f"Pinecone delete error: {e}")
            return False
    
    def get_provider_name(self) -> str:
        return "pinecone"


class AzureAISearchVectorAdapter(VectorAdapter):
    """Azure AI Search with vector support (Azure native)"""
    
    def __init__(self):
        self.endpoint = os.getenv('AZURE_SEARCH_ENDPOINT')
        self.api_key = os.getenv('AZURE_SEARCH_API_KEY')
        self.index_name = os.getenv('AZURE_SEARCH_INDEX', 'rag-vectors')
        self._client = None
        
        if not self.endpoint or not self.api_key:
            logger.warning("Azure AI Search not configured")
    
    def _get_client(self):
        """Lazy initialization"""
        if self._client is None:
            try:
                from azure.search.documents import SearchClient
                from azure.core.credentials import AzureKeyCredential
                
                self._client = SearchClient(
                    endpoint=self.endpoint,
                    index_name=self.index_name,
                    credential=AzureKeyCredential(self.api_key)
                )
            except Exception as e:
                logger.error(f"Azure AI Search init failed: {e}")
        return self._client
    
    def query(
        self,
        vector: List[float],
        top_k: int = 5,
        filter: Optional[Dict] = None
    ) -> List[Dict]:
        try:
            client = self._get_client()
            if not client:
                return []
            
            # Azure AI Search vector query
            results = client.search(
                search_text="",
                vector_queries=[{
                    "kind": "vector",
                    "vector": vector,
                    "k": top_k,
                    "fields": "embedding"
                }]
            )
            
            return [{
                'id': doc['id'],
                'score': doc.get('@search.score', 0),
                'metadata': {k: v for k, v in doc.items() if k not in ['id', 'embedding', '@search.score']},
                'values': []  # Don't return vectors by default
            } for doc in results]
            
        except Exception as e:
            logger.error(f"Azure AI Search query error: {e}")
            return []
    
    def upsert(self, vectors: List[Dict]) -> bool:
        try:
            client = self._get_client()
            if not client:
                return False
            
            # Transform to Azure AI Search format
            documents = [{
                'id': vec['id'],
                'embedding': vec['values'],
                **vec.get('metadata', {})
            } for vec in vectors]
            
            client.upload_documents(documents=documents)
            return True
            
        except Exception as e:
            logger.error(f"Azure AI Search upsert error: {e}")
            return False
    
    def delete(self, ids: List[str]) -> bool:
        try:
            client = self._get_client()
            if not client:
                return False
            
            client.delete_documents(documents=[{'id': id} for id in ids])
            return True
            
        except Exception as e:
            logger.error(f"Azure AI Search delete error: {e}")
            return False
    
    def get_provider_name(self) -> str:
        return "azure_ai_search"


def get_vector_adapter() -> VectorAdapter:
    """
    Get vector adapter based on environment config
    Priority: Azure AI Search → Pinecone (default)
    """
    vector_provider = os.getenv('VECTOR_PROVIDER', 'auto').lower()
    
    if vector_provider == 'azure_ai_search' or (vector_provider == 'auto' and os.getenv('AZURE_SEARCH_ENDPOINT')):
        logger.info("Using Azure AI Search for vectors")
        return AzureAISearchVectorAdapter()
    
    else:
        logger.info("Using Pinecone for vectors (default)")
        return PineconeVectorAdapter()
