"""
Advanced Conversational RAG Service
Implements multi-query retrieval, deduplication, MMR, and session management
"""

from typing import List, Dict, Optional, Set, Tuple
from openai import OpenAI
import os
from dataclasses import dataclass, field
import numpy as np
import time
import logging
from functools import wraps

from app.core.pinecone_db import get_pinecone_index
from app.core.settings import settings

# Lazy initialization - only create client when needed
_client = None

def get_openai_client():
    """Get or create OpenAI client lazily"""
    global _client
    if _client is None:
        _client = OpenAI(api_key=settings.OPENAI_API_KEY)
    return _client

logger = logging.getLogger(__name__)

# Session cleanup configuration
SESSION_TTL_SECONDS = 3600  # 1 hour
MAX_SESSIONS = 1000  # Prevent memory bloat


def retry_with_exponential_backoff(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    exponential_base: float = 2.0,
    max_delay: float = 10.0
):
    """Retry decorator with exponential backoff for API calls"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        logger.warning(
                            f"{func.__name__} failed (attempt {attempt + 1}/{max_retries}): {e}. "
                            f"Retrying in {delay}s..."
                        )
                        time.sleep(delay)
                        delay = min(delay * exponential_base, max_delay)
                    else:
                        logger.error(f"{func.__name__} failed after {max_retries} attempts: {e}")
            
            raise last_exception
        return wrapper
    return decorator


@dataclass
class ConversationState:
    """Tracks conversation state for a session"""
    session_id: str
    shown_chunk_ids: Set[str] = field(default_factory=set)
    topics_covered: List[str] = field(default_factory=list)
    last_query: Optional[str] = None
    turn_count: int = 0
    last_access: float = field(default_factory=time.time)
    
    def touch(self):
        """Update last access time"""
        self.last_access = time.time()


# In-memory session store (TODO: Replace with Redis for production)
_session_store: Dict[str, ConversationState] = {}


def cleanup_old_sessions():
    """Remove expired sessions to prevent memory leaks"""
    now = time.time()
    expired_sessions = [
        session_id for session_id, state in _session_store.items()
        if (now - state.last_access) > SESSION_TTL_SECONDS
    ]
    
    for session_id in expired_sessions:
        del _session_store[session_id]
        logger.info(f"Cleaned up expired session: {session_id}")
    
    # If still too many sessions, remove oldest
    if len(_session_store) > MAX_SESSIONS:
        sorted_sessions = sorted(
            _session_store.items(),
            key=lambda x: x[1].last_access
        )
        to_remove = len(_session_store) - MAX_SESSIONS
        for session_id, _ in sorted_sessions[:to_remove]:
            del _session_store[session_id]
            logger.info(f"Cleaned up old session (max limit): {session_id}")
    
    if expired_sessions or len(_session_store) > MAX_SESSIONS:
        logger.info(f"Session cleanup complete. Active sessions: {len(_session_store)}")


def get_or_create_session(session_id: str) -> ConversationState:
    """Get existing session or create new one"""
    # Periodic cleanup (every 10th request)
    if len(_session_store) % 10 == 0:
        cleanup_old_sessions()
    
    if session_id not in _session_store:
        logger.info(f"Creating new session: {session_id}")
        _session_store[session_id] = ConversationState(session_id=session_id)
    
    state = _session_store[session_id]
    state.touch()  # Update last access
    return state


@retry_with_exponential_backoff(max_retries=3)
def expand_query_with_context(
    query: str,
    conversation_history: Optional[List[Dict]] = None
) -> str:
    """
    Expand query using conversation context
    Handles pronouns, references, and follow-up patterns
    """
    if not conversation_history or len(conversation_history) == 0:
        return query
    
    # Build conversation context (last 2 exchanges)
    recent_history = conversation_history[-4:] if len(conversation_history) > 4 else conversation_history
    context_str = "\n".join([
        f"{msg['role']}: {msg['content'][:200]}..."
        for msg in recent_history
    ])
    
    expansion_prompt = f"""Given this conversation history:

{context_str}

Current user query: "{query}"

If the query is vague, contains pronouns (it, that, this), or is a follow-up (tell me more, what about, why), expand it into a complete, standalone question that incorporates relevant context from the conversation.

If the query is already clear and specific, return it as-is.

Expanded query:"""
    
    response = get_openai_client().chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a query expansion assistant. Rewrite vague queries into clear, specific questions."},
            {"role": "user", "content": expansion_prompt}
        ],
        temperature=0.3,
        max_tokens=150
    )
    expanded = response.choices[0].message.content.strip()
    logger.debug(f"Query expanded: '{query}' -> '{expanded}'")
    return expanded


@retry_with_exponential_backoff(max_retries=2)  # Fewer retries for non-critical
def generate_multi_queries(query: str, num_variants: int = 3) -> List[str]:
    """
    Generate multiple query variants for better coverage
    """
    prompt = f"""Generate {num_variants} different ways to search for information about this question:

"{query}"

Create variants that:
1. Use different terminology (technical vs plain language)
2. Focus on different aspects (causes, effects, data, policy)
3. Vary in specificity (broad vs narrow)

Return ONLY the {num_variants} query variants, one per line, without numbering or explanation."""
    
    response = get_openai_client().chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a search query generator. Create diverse query variants."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=200
    )
    variants = response.choices[0].message.content.strip().split('\n')
    variants = [v.strip() for v in variants if v.strip()]
    
    # Include original query
    all_queries = [query] + variants[:num_variants]
    logger.debug(f"Generated {len(all_queries)} query variants")
    return all_queries


def retrieve_with_deduplication(
    query: str,
    shown_ids: Set[str],
    top_k: int = 5,
    over_retrieve_factor: int = 3
) -> List[Dict]:
    """
    Retrieve documents with deduplication
    Over-retrieves and filters out already-shown chunks
    """
    index = get_pinecone_index()
    
    # Generate embedding
    embedding_response = get_openai_client().embeddings.create(
        model="text-embedding-3-large",
        input=query
    )
    query_embedding = embedding_response.data[0].embedding
    
    # Over-retrieve to account for deduplication
    retrieve_k = top_k * over_retrieve_factor
    
    results = index.query(
        vector=query_embedding,
        top_k=retrieve_k,
        include_metadata=True,
        include_values=True  # Include vectors for MMR without re-embedding
    )
    
    # Filter out shown chunks
    new_chunks = []
    for match in results['matches']:
        if match['id'] not in shown_ids:
            new_chunks.append({
                'id': match['id'],
                'score': match['score'],
                'metadata': match.get('metadata', {}),
                'values': match.get('values', []),  # Store Pinecone vector for MMR
                'query_embedding': query_embedding  # Store query embedding for MMR
            })
        
        if len(new_chunks) >= top_k:
            break
    
    return new_chunks


def reciprocal_rank_fusion(
    result_sets: List[List[Dict]],
    k: int = 60
) -> List[Dict]:
    """
    Fuse multiple result sets using Reciprocal Rank Fusion
    
    Formula: RRF(d) = Σ 1/(k + rank_i(d))
    """
    # Calculate RRF scores
    doc_scores = {}
    
    for result_set in result_sets:
        for rank, doc in enumerate(result_set, start=1):
            doc_id = doc['id']
            rrf_score = 1.0 / (k + rank)
            
            if doc_id not in doc_scores:
                doc_scores[doc_id] = {
                    'rrf_score': 0.0,
                    'doc': doc
                }
            doc_scores[doc_id]['rrf_score'] += rrf_score
    
    # Sort by RRF score
    sorted_docs = sorted(
        doc_scores.values(),
        key=lambda x: x['rrf_score'],
        reverse=True
    )
    
    return [item['doc'] for item in sorted_docs]


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calculate cosine similarity between two vectors"""
    vec1_np = np.array(vec1)
    vec2_np = np.array(vec2)
    
    dot_product = np.dot(vec1_np, vec2_np)
    norm1 = np.linalg.norm(vec1_np)
    norm2 = np.linalg.norm(vec2_np)
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    return dot_product / (norm1 * norm2)


def maximal_marginal_relevance(
    chunks: List[Dict],
    query_embedding: List[float],
    k: int = 5,
    lambda_param: float = 0.6
) -> List[Dict]:
    """
    Select diverse chunks using MMR - Optimized version using Pinecone vectors
    
    MMR = λ × sim(q, d) - (1-λ) × max[sim(d, d')]
    """
    if len(chunks) <= k:
        return chunks
    
    # Use embeddings from Pinecone (already included in chunk)
    chunk_embeddings = []
    for chunk in chunks:
        # Use Pinecone vector if available, otherwise use query embedding as fallback
        if 'values' in chunk and chunk['values']:
            chunk_embeddings.append(chunk['values'])
        else:
            # Fallback to query embedding (won't provide diversity but prevents errors)
            chunk_embeddings.append(query_embedding)
            logger.warning(f"Missing vector for chunk {chunk.get('id')}, using query embedding")
    
    selected_indices = []
    remaining_indices = list(range(len(chunks)))
    
    # Select first (most relevant)
    first_idx = 0  # Already sorted by relevance
    selected_indices.append(first_idx)
    remaining_indices.remove(first_idx)
    
    # Select remaining using MMR
    while len(selected_indices) < k and remaining_indices:
        mmr_scores = []
        
        for idx in remaining_indices:
            # Relevance to query
            relevance = cosine_similarity(query_embedding, chunk_embeddings[idx])
            
            # Max similarity to selected
            max_sim = max([
                cosine_similarity(chunk_embeddings[idx], chunk_embeddings[sel_idx])
                for sel_idx in selected_indices
            ])
            
            mmr = lambda_param * relevance - (1 - lambda_param) * max_sim
            mmr_scores.append((idx, mmr))
        
        # Select highest MMR
        best_idx = max(mmr_scores, key=lambda x: x[1])[0]
        selected_indices.append(best_idx)
        remaining_indices.remove(best_idx)
    
    return [chunks[i] for i in selected_indices]


def detect_topic_shift(current_query: str, last_query: Optional[str]) -> bool:
    """
    Detect if query represents a topic shift vs continuation
    """
    if not last_query:
        return False
    
    # Embed both queries
    try:
        response = get_openai_client().embeddings.create(
            model="text-embedding-3-large",
            input=[current_query, last_query]
        )
        
        current_emb = response.data[0].embedding
        last_emb = response.data[1].embedding
        
        similarity = cosine_similarity(current_emb, last_emb)
        
        # Threshold: < 0.3 = topic shift
        return similarity < 0.3
    except:
        return False


def conversational_retrieve(
    query: str,
    session_id: str,
    conversation_history: Optional[List[Dict]] = None,
    top_k: int = 5
) -> Tuple[List[Dict], ConversationState]:
    """
    Main conversational retrieval pipeline
    
    Steps:
    1. Get/create session state
    2. Detect topic shift
    3. Expand query with context
    4. Generate multi-queries
    5. Retrieve with deduplication
    6. Fuse results (RRF)
    7. Apply MMR for diversity
    8. Update session state
    """
    
    try:
        # Step 1: Session management
        state = get_or_create_session(session_id)
        state.turn_count += 1
        
        # Step 2: Topic shift detection
        try:
            topic_shifted = detect_topic_shift(query, state.last_query)
            if topic_shifted:
                state.shown_chunk_ids.clear()
                logger.info(f"Topic shift detected for session {session_id}")
        except Exception as e:
            logger.warning(f"Topic shift detection failed: {e}. Continuing...")
            topic_shifted = False
        
        # Step 3: Query expansion
        try:
            expanded_query = expand_query_with_context(query, conversation_history)
            logger.info(f"Expanded query: {expanded_query}")
        except Exception as e:
            logger.warning(f"Query expansion failed: {e}. Using original query.")
            expanded_query = query
        
        # Step 4: Multi-query generation
        try:
            query_variants = generate_multi_queries(expanded_query, num_variants=2)
            logger.info(f"Generated {len(query_variants)} query variants")
        except Exception as e:
            logger.warning(f"Multi-query generation failed: {e}. Using single query.")
            query_variants = [expanded_query]
        
        # Step 5: Retrieve for each variant with deduplication
        all_result_sets = []
        for variant in query_variants:
            try:
                results = retrieve_with_deduplication(
                    variant,
                    state.shown_chunk_ids,
                    top_k=top_k,
                    over_retrieve_factor=3
                )
                if results:
                    all_result_sets.append(results)
            except Exception as e:
                logger.warning(f"Retrieval failed for variant '{variant}': {e}")
                continue
        
        if not all_result_sets:
            # Fallback: No new results, allow re-use
            logger.info("No new chunks found, allowing re-use")
            state.shown_chunk_ids.clear()
            try:
                results = retrieve_with_deduplication(
                    expanded_query,
                    state.shown_chunk_ids,
                    top_k=top_k
                )
                all_result_sets = [results] if results else []
            except Exception as e:
                logger.error(f"Fallback retrieval also failed: {e}")
                return [], state
        
        if not all_result_sets:
            logger.warning(f"No results found for query: {query}")
            return [], state
        
        # Step 6: RRF fusion
        fused_results = reciprocal_rank_fusion(all_result_sets)
        
        # Step 7: Get query embedding for MMR
        try:
            emb_response = get_openai_client().embeddings.create(
                model="text-embedding-3-large",
                input=expanded_query
            )
            query_embedding = emb_response.data[0].embedding
            
            # Step 7: MMR for diversity
            final_results = maximal_marginal_relevance(
                fused_results[:top_k * 2],
                query_embedding,
                k=top_k,
                lambda_param=0.6
            )
        except Exception as e:
            logger.warning(f"MMR failed: {e}. Using fused results directly.")
            final_results = fused_results[:top_k]
        
        # Step 8: Update session state
        for chunk in final_results:
            state.shown_chunk_ids.add(chunk['id'])
        state.last_query = query
        state.touch()
        
        logger.info(
            f"Retrieved {len(final_results)} chunks for session {session_id}, "
            f"turn {state.turn_count}, shown_total: {len(state.shown_chunk_ids)}"
        )
        
        return final_results, state
        
    except Exception as e:
        logger.error(f"Conversational retrieve failed completely: {e}", exc_info=True)
        # Return empty results but maintain session state
        state = get_or_create_session(session_id)
        return [], state
