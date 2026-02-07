"""
GraphRAG Retrieval Service - Fact-based retrieval with graph traversal
Combines vector similarity search with graph-based reasoning
"""

import logging
from typing import List, Dict, Optional, Tuple
from pinecone import Pinecone
import os
from openai import OpenAI
import json

from app.models.fact import RAGIngressFact, FactSearchQuery, FactGraph

logger = logging.getLogger(__name__)


class GraphRAGRetriever:
    """Retrieve and reason over structured facts using hybrid vector + graph approach"""
    
    def __init__(
        self,
        pinecone_index_name: str = "ecosurvey-facts",
        embedding_model: str = "text-embedding-3-large"
    ):
        # Initialize Pinecone for vector search
        pc = Pinecone(api_key=os.getenv('PINECONE_API_KEY'))
        self.index = pc.Index(pinecone_index_name)
        
        # Initialize OpenAI for embeddings and reasoning
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.embedding_model = embedding_model
        
    def retrieve_facts(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict] = None
    ) -> List[RAGIngressFact]:
        """
        Retrieve relevant facts using vector similarity
        
        Args:
            query: Natural language query
            top_k: Number of facts to retrieve
            filters: Metadata filters (source_origin, entities, temporal_context)
            
        Returns:
            List of relevant facts
        """
        
        # Generate query embedding
        query_embedding = self._get_embedding(query)
        
        # Build metadata filter
        metadata_filter = {}
        if filters:
            if 'source_origin' in filters:
                metadata_filter['source_origin'] = {"$in": filters['source_origin']}
            if 'entities' in filters:
                metadata_filter['entities'] = {"$in": filters['entities']}
            if 'min_certainty' in filters:
                metadata_filter['certainty_score'] = {"$gte": filters['min_certainty']}
        
        # Query Pinecone
        results = self.index.query(
            vector=query_embedding,
            top_k=top_k,
            include_metadata=True,
            filter=metadata_filter if metadata_filter else None
        )
        
        # Convert to RAGIngressFact objects
        facts = []
        for match in results['matches']:
            fact_data = match['metadata']
            
            # Reconstruct fact from metadata
            fact = RAGIngressFact(
                fact_id=match['id'],
                parent_context_id=fact_data.get('parent_context_id'),
                source_origin=fact_data['source_origin'],
                page_reference=fact_data['page_reference'],
                document_id=fact_data.get('document_id'),
                subject=fact_data['subject'],
                predicate=fact_data['predicate'],
                value_quantity=fact_data.get('value_quantity'),
                value_unit=fact_data.get('value_unit'),
                temporal_context=fact_data.get('temporal_context'),
                modality=fact_data['modality'],
                certainty_score=fact_data['certainty_score'],
                sentiment_magnitude=fact_data['sentiment_magnitude'],
                verbatim_extraction=fact_data['verbatim_extraction'],
                related_entities=fact_data.get('related_entities', []),
                related_facts=fact_data.get('related_facts', []),
                extraction_model=fact_data.get('extraction_model', 'unknown'),
                confidence_score=match['score']  # Use similarity score as confidence
            )
            facts.append(fact)
        
        logger.info(f"Retrieved {len(facts)} facts for query: {query[:50]}...")
        return facts
    
    def build_fact_graph(
        self,
        seed_facts: List[RAGIngressFact],
        max_depth: int = 2
    ) -> FactGraph:
        """
        Build a connected subgraph by traversing related_facts links
        
        Args:
            seed_facts: Initial facts to start traversal
            max_depth: Maximum hops to traverse
            
        Returns:
            Connected graph of facts with reasoning path
        """
        
        if not seed_facts:
            return FactGraph(
                root_fact_id="",
                connected_facts=[],
                reasoning_path=["No seed facts provided"]
            )
        
        root_fact = seed_facts[0]
        visited_ids = {root_fact.fact_id}
        connected_facts = [root_fact]
        reasoning_path = [f"Starting from: {root_fact.subject} {root_fact.predicate}"]
        
        # BFS traversal through related_facts
        queue = [(root_fact, 0)]  # (fact, depth)
        
        while queue and len(connected_facts) < 20:  # Limit graph size
            current_fact, depth = queue.pop(0)
            
            if depth >= max_depth:
                continue
            
            # Traverse related facts
            for related_id in current_fact.related_facts:
                if related_id in visited_ids:
                    continue
                
                # Fetch related fact from Pinecone
                related_fact = self._fetch_fact_by_id(related_id)
                if related_fact:
                    visited_ids.add(related_id)
                    connected_facts.append(related_fact)
                    reasoning_path.append(
                        f"→ Related: {related_fact.subject} {related_fact.predicate}"
                    )
                    queue.append((related_fact, depth + 1))
        
        # Calculate aggregated confidence
        avg_confidence = sum(f.confidence_score for f in connected_facts) / len(connected_facts)
        
        return FactGraph(
            root_fact_id=root_fact.fact_id,
            connected_facts=connected_facts,
            reasoning_path=reasoning_path,
            aggregated_confidence=avg_confidence
        )
    
    def answer_with_reasoning(
        self,
        query: str,
        top_k: int = 5,
        use_graph: bool = True
    ) -> Dict:
        """
        Answer query with explicit reasoning over facts
        
        Args:
            query: Natural language question
            top_k: Number of facts to retrieve
            use_graph: Whether to build fact graph for multi-hop reasoning
            
        Returns:
            Dict with answer, reasoning steps, and supporting facts
        """
        
        # Step 1: Retrieve relevant facts
        facts = self.retrieve_facts(query, top_k=top_k)
        
        if not facts:
            return {
                "answer": "I couldn't find relevant information to answer your question.",
                "reasoning_steps": ["No facts retrieved"],
                "supporting_facts": [],
                "confidence": 0.0
            }
        
        # Step 2: Build fact graph if requested
        fact_graph = None
        if use_graph:
            fact_graph = self.build_fact_graph(facts, max_depth=2)
            facts = fact_graph.connected_facts
        
        # Step 3: Generate answer with LLM reasoning over facts
        answer_response = self._generate_answer(query, facts, fact_graph)
        
        return answer_response
    
    def _generate_answer(
        self,
        query: str,
        facts: List[RAGIngressFact],
        fact_graph: Optional[FactGraph] = None
    ) -> Dict:
        """Generate answer from facts using LLM with chain-of-thought reasoning"""
        
        # Build context from facts
        context = self._format_facts_as_context(facts)
        
        reasoning_path = fact_graph.reasoning_path if fact_graph else []
        
        system_prompt = """You are an economic analyst answering questions using ONLY the structured facts provided.

CRITICAL RULES:
1. ONLY use information from the provided facts
2. Cite fact IDs in your answer using [fact_id]
3. Show your reasoning step-by-step
4. If facts contradict, acknowledge the discrepancy
5. Weight facts by certainty_score (higher = more reliable)
6. Note temporal context (historical vs current vs projected)
7. If insufficient information, say so explicitly

RESPONSE FORMAT:
{
  "answer": "Direct answer with [fact_id] citations",
  "reasoning_steps": ["Step 1: ...", "Step 2: ..."],
  "confidence": 0.85,
  "caveats": ["Any limitations or uncertainties"]
}"""
        
        user_prompt = f"""QUESTION: {query}

AVAILABLE FACTS:
{context}

Graph traversal path:
{chr(10).join(reasoning_path) if reasoning_path else 'Direct retrieval (no graph traversal)'}

Provide a well-reasoned answer using ONLY these facts. Include fact IDs as citations."""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            result['supporting_facts'] = [
                {
                    'fact_id': f.fact_id,
                    'subject': f.subject,
                    'predicate': f.predicate,
                    'value': f"{f.value_quantity} {f.value_unit}" if f.value_quantity else None,
                    'source': f"{f.source_origin}, p.{f.page_reference}",
                    'certainty': f.certainty_score,
                    'verbatim': f.verbatim_extraction
                }
                for f in facts[:5]  # Top 5 facts
            ]
            
            return result
            
        except Exception as e:
            logger.error(f"Answer generation failed: {e}")
            return {
                "answer": "Error generating answer",
                "reasoning_steps": [str(e)],
                "supporting_facts": [],
                "confidence": 0.0
            }
    
    def _format_facts_as_context(self, facts: List[RAGIngressFact]) -> str:
        """Format facts into readable context for LLM"""
        
        context_lines = []
        for i, fact in enumerate(facts, 1):
            value_str = f"{fact.value_quantity} {fact.value_unit}" if fact.value_quantity else ""
            temporal_str = f"({fact.temporal_context})" if fact.temporal_context else ""
            
            context_lines.append(
                f"[{fact.fact_id}] {fact.subject} {fact.predicate} {value_str} {temporal_str}\n"
                f"  Source: {fact.source_origin}, p.{fact.page_reference}\n"
                f"  Certainty: {fact.certainty_score:.2f}, Sentiment: {fact.sentiment_magnitude:+.2f}\n"
                f"  Quote: \"{fact.verbatim_extraction}\"\n"
                f"  Entities: {', '.join(fact.related_entities)}"
            )
        
        return "\n\n".join(context_lines)
    
    def _get_embedding(self, text: str) -> List[float]:
        """Generate embedding for text"""
        response = self.client.embeddings.create(
            input=text,
            model=self.embedding_model
        )
        return response.data[0].embedding
    
    def _fetch_fact_by_id(self, fact_id: str) -> Optional[RAGIngressFact]:
        """Fetch a fact from Pinecone by ID"""
        try:
            result = self.index.fetch(ids=[fact_id])
            if fact_id in result['vectors']:
                fact_data = result['vectors'][fact_id]['metadata']
                return RAGIngressFact(**fact_data)
        except Exception as e:
            logger.warning(f"Failed to fetch fact {fact_id}: {e}")
        return None
