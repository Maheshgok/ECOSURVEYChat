"""
Fact Extraction Service - Transform unstructured chunks into structured facts
Uses OpenAI GPT-4 to extract atomic facts from document chunks
"""

import json
import logging
from typing import List, Optional, Dict
from openai import OpenAI
import os

from app.models.fact import RAGIngressFact, FactExtractionPrompt

logger = logging.getLogger(__name__)


class FactExtractor:
    """Extract structured facts from unstructured text using LLM"""
    
    def __init__(self, model: str = "gpt-4o-mini"):
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.model = model
        
    def extract_facts(
        self,
        chunk_text: str,
        source_origin: str,
        page_reference: int,
        document_id: Optional[str] = None,
        parent_context_id: Optional[str] = None
    ) -> List[RAGIngressFact]:
        """
        Extract atomic facts from a text chunk
        
        Args:
            chunk_text: Raw text to extract facts from
            source_origin: Document type (Economic_Survey, Union_Budget, etc.)
            page_reference: Page number in source document
            document_id: Unique document identifier
            parent_context_id: ID of previous chunk for narrative flow
            
        Returns:
            List of extracted facts
        """
        
        prompt = self._build_extraction_prompt(
            chunk_text, 
            source_origin, 
            page_reference,
            document_id,
            parent_context_id
        )
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": prompt["system"]},
                    {"role": "user", "content": prompt["user"]}
                ],
                temperature=0.1,  # Low temperature for factual extraction
                response_format={"type": "json_object"}
            )
            
            facts_json = json.loads(response.choices[0].message.content)
            facts = [RAGIngressFact(**fact) for fact in facts_json.get("facts", [])]
            
            logger.info(f"Extracted {len(facts)} facts from chunk (page {page_reference})")
            return facts
            
        except Exception as e:
            logger.error(f"Fact extraction failed: {e}")
            return []
    
    def _build_extraction_prompt(
        self,
        chunk_text: str,
        source_origin: str,
        page_reference: int,
        document_id: Optional[str],
        parent_context_id: Optional[str]
    ) -> Dict[str, str]:
        """Build structured prompt for fact extraction"""
        
        system_prompt = """You are a financial document analyst extracting structured facts for a knowledge graph.

EXTRACTION RULES:
1. Break each paragraph into atomic facts (subject-predicate-value triples)
2. Extract numerical values separately with units (%, Cr, bps, USD)
3. Capture temporal context (FY2025-26, Q3 2024, etc.)
4. Rate certainty: 
   - 1.0 for definitive statements ("The deficit IS 4.5%")
   - 0.8 for planned/targeted ("The deficit is TARGETED at 4.5%")
   - 0.5 for conditional ("The deficit MAY reach 4.5%")
   - 0.0 for speculative ("The deficit COULD potentially reach 4.5%")
5. Rate sentiment:
   - -1.0 for contractionary/hawkish (rate hikes, spending cuts, tightening)
   - 0.0 neutral (status quo, maintenance)
   - +1.0 expansionary/dovish (rate cuts, spending increases, stimulus)
6. Always include verbatim_extraction (exact quote from text) for verification
7. Tag entities for graph traversal (e.g., Agriculture, GDP, Fiscal Policy)
8. Identify relationships between facts (same entity, causal links, temporal sequences)

RESPONSE FORMAT:
{
  "facts": [
    {
      "subject": "string",
      "predicate": "string",
      "value_quantity": float or null,
      "value_unit": "string" or null,
      "temporal_context": "string" or null,
      "modality": "Mandatory|Provisional|Aspirational|Historical",
      "certainty_score": float (0.0-1.0),
      "sentiment_magnitude": float (-1.0 to +1.0),
      "verbatim_extraction": "exact quote from text",
      "related_entities": ["entity1", "entity2"],
      "related_facts": []
    }
  ]
}

EXAMPLE INPUT: "The fiscal deficit is targeted at 4.5% of GDP for FY2025-26, down from 5.2% in FY2024-25."

EXAMPLE OUTPUT:
{
  "facts": [
    {
      "subject": "Fiscal Deficit",
      "predicate": "Targeted at",
      "value_quantity": 4.5,
      "value_unit": "%",
      "temporal_context": "FY2025-26",
      "modality": "Aspirational",
      "certainty_score": 0.8,
      "sentiment_magnitude": -0.3,
      "verbatim_extraction": "The fiscal deficit is targeted at 4.5% of GDP for FY2025-26",
      "related_entities": ["Fiscal Policy", "GDP", "Budget 2026"],
      "related_facts": []
    },
    {
      "subject": "Fiscal Deficit",
      "predicate": "Was",
      "value_quantity": 5.2,
      "value_unit": "%",
      "temporal_context": "FY2024-25",
      "modality": "Historical",
      "certainty_score": 1.0,
      "sentiment_magnitude": 0.0,
      "verbatim_extraction": "down from 5.2% in FY2024-25",
      "related_entities": ["Fiscal Policy", "GDP", "Budget 2025"],
      "related_facts": []
    }
  ]
}"""
        
        user_prompt = f"""Extract atomic facts from this text chunk:

SOURCE: {source_origin}
PAGE: {page_reference}
DOCUMENT_ID: {document_id or 'unknown'}

TEXT:
{chunk_text}

Return ONLY the JSON object with extracted facts. No additional commentary."""
        
        return {
            "system": system_prompt,
            "user": user_prompt
        }
    
    def batch_extract(
        self,
        chunks: List[Dict],
        source_origin: str
    ) -> List[RAGIngressFact]:
        """
        Extract facts from multiple chunks in sequence
        
        Args:
            chunks: List of dicts with 'text', 'page', 'chunk_id'
            source_origin: Document type
            
        Returns:
            Flattened list of all extracted facts
        """
        all_facts = []
        previous_chunk_id = None
        
        for chunk in chunks:
            facts = self.extract_facts(
                chunk_text=chunk['text'],
                source_origin=source_origin,
                page_reference=chunk.get('page', 0),
                document_id=chunk.get('document_id'),
                parent_context_id=previous_chunk_id
            )
            
            # Link facts to previous chunk for narrative flow
            if facts and previous_chunk_id:
                # Update parent_context_id for first fact in this chunk
                facts[0].parent_context_id = previous_chunk_id
            
            all_facts.extend(facts)
            
            # Update parent context for next iteration
            if facts:
                previous_chunk_id = facts[-1].fact_id
        
        logger.info(f"Batch extraction complete: {len(all_facts)} total facts from {len(chunks)} chunks")
        return all_facts


# Example usage
if __name__ == "__main__":
    extractor = FactExtractor()
    
    sample_text = """
    The fiscal deficit is targeted at 4.5% of GDP for FY2025-26, down from 5.2% 
    in FY2024-25. This reduction reflects the government's commitment to fiscal 
    consolidation. Capital expenditure is projected to increase by 15% to 
    ₹12 lakh crore, focusing on infrastructure development in tier-2 cities.
    """
    
    facts = extractor.extract_facts(
        chunk_text=sample_text,
        source_origin="Economic_Survey",
        page_reference=42,
        document_id="eco_survey_2026_ch3"
    )
    
    print(f"\nExtracted {len(facts)} facts:")
    for fact in facts:
        print(f"\n- {fact.subject} {fact.predicate} {fact.value_quantity} {fact.value_unit}")
        print(f"  Certainty: {fact.certainty_score}, Sentiment: {fact.sentiment_magnitude}")
        print(f"  Source: \"{fact.verbatim_extraction}\"")
