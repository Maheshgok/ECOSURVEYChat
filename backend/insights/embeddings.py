"""Embedding service for text vectorization and similarity search"""

from typing import List, Dict, Tuple
import re
from collections import Counter
import math


class EmbeddingService:
    """Simple TF-IDF based embedding service for MVP"""
    
    def __init__(self, vocabulary: Dict[str, int] = None):
        """
        Initialize embedding service
        
        Args:
            vocabulary: Optional pre-computed vocabulary
        """
        self.vocabulary = vocabulary or {}
        self.embedding_dim = 100
    
    def embed_text(self, text: str) -> List[float]:
        """
        Create TF-IDF embedding from text
        
        Args:
            text: Text to embed
            
        Returns:
            Vector of floats (TF-IDF scores)
        """
        # Tokenize
        tokens = self._tokenize(text)
        if not tokens:
            return [0.0] * self.embedding_dim
        
        # Calculate term frequencies
        tf = self._calculate_tf(tokens)
        
        # Build embedding from top terms
        embedding = self._build_embedding(tf)
        
        return embedding
    
    def embed_insight(self, insight: Dict) -> List[float]:
        """
        Create embedding from insight data
        
        Args:
            insight: Insight dictionary with metric, value, description
            
        Returns:
            Vector of floats
        """
        # Combine insight components into text
        parts = []
        
        if 'metric' in insight:
            parts.append(str(insight['metric']))
        
        if 'value' in insight:
            parts.append(str(insight['value']))
        
        if 'description' in insight:
            parts.append(str(insight['description']))
        
        text = " ".join(parts)
        
        return self.embed_text(text)
    
    def similarity(self, embed1: List[float], embed2: List[float]) -> float:
        """
        Calculate cosine similarity between embeddings
        
        Args:
            embed1: First embedding vector
            embed2: Second embedding vector
            
        Returns:
            Similarity score 0-1
        """
        if not embed1 or not embed2:
            return 0.0
        
        # Cosine similarity
        dot_product = sum(a * b for a, b in zip(embed1, embed2))
        
        norm1 = math.sqrt(sum(a * a for a in embed1))
        norm2 = math.sqrt(sum(b * b for b in embed2))
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def similarity_search(
        self,
        query_embedding: List[float],
        candidate_embeddings: List[Tuple[str, List[float]]],
        top_k: int = 5,
        threshold: float = 0.3
    ) -> List[Tuple[str, float]]:
        """
        Find top-k most similar embeddings
        
        Args:
            query_embedding: Query vector
            candidate_embeddings: List of (id, embedding) tuples
            top_k: Number of results to return
            threshold: Minimum similarity score
            
        Returns:
            List of (id, similarity_score) tuples, sorted by score
        """
        results = []
        
        for item_id, embedding in candidate_embeddings:
            score = self.similarity(query_embedding, embedding)
            if score >= threshold:
                results.append((item_id, score))
        
        # Sort by similarity descending
        results.sort(key=lambda x: x[1], reverse=True)
        
        return results[:top_k]
    
    def _tokenize(self, text: str) -> List[str]:
        """
        Tokenize text into words
        
        Args:
            text: Text to tokenize
            
        Returns:
            List of tokens
        """
        # Convert to lowercase and remove punctuation
        text = text.lower()
        text = re.sub(r'[^\w\s]', '', text)
        
        # Split on whitespace
        tokens = text.split()
        
        # Remove empty and short tokens
        tokens = [t for t in tokens if len(t) > 2]
        
        return tokens
    
    def _calculate_tf(self, tokens: List[str]) -> Dict[str, float]:
        """
        Calculate term frequency (TF)
        
        Args:
            tokens: List of tokens
            
        Returns:
            Dict of {term: tf_score}
        """
        if not tokens:
            return {}
        
        # Count occurrences
        counts = Counter(tokens)
        total = len(tokens)
        
        # Calculate TF as count / total
        tf = {}
        for term, count in counts.items():
            tf[term] = count / total
        
        return tf
    
    def _build_embedding(self, tf: Dict[str, float]) -> List[float]:
        """
        Build embedding vector from TF scores
        
        Args:
            tf: Term frequency dictionary
            
        Returns:
            Embedding vector of fixed dimension
        """
        embedding = [0.0] * self.embedding_dim
        
        if not tf:
            return embedding
        
        # Sort terms by TF score
        sorted_terms = sorted(tf.items(), key=lambda x: x[1], reverse=True)
        
        # Fill embedding with TF scores
        for i, (term, score) in enumerate(sorted_terms):
            if i >= self.embedding_dim:
                break
            
            # Weight by term position (higher terms get higher weight)
            weight = 1.0 - (i / len(sorted_terms))
            embedding[i] = score * weight
        
        # Normalize embedding
        norm = math.sqrt(sum(x * x for x in embedding))
        if norm > 0:
            embedding = [x / norm for x in embedding]
        
        return embedding
    
    def batch_embed(self, texts: List[str]) -> List[List[float]]:
        """
        Create embeddings for multiple texts
        
        Args:
            texts: List of text strings
            
        Returns:
            List of embedding vectors
        """
        return [self.embed_text(text) for text in texts]
