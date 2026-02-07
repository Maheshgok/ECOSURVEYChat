"""
GraphRAG Fact Model - Structured Knowledge Representation
Transforms unstructured chunks into verifiable, graph-traversable facts
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime
import uuid


class RAGIngressFact(BaseModel):
    """
    Atomic fact unit for GraphRAG ingestion.
    Each fact represents a single verifiable statement from source documents.
    """
    
    # --- IDENTIFICATION & LINKAGE ---
    fact_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    parent_context_id: Optional[str] = Field(
        None, 
        description="Links to the previous logical sentence/chunk to maintain narrative flow"
    )
    source_origin: Literal[
        "Union_Budget", 
        "RBI_Circular", 
        "Economic_Survey", 
        "CEO_Transcript",
        "Policy_Document",
        "Research_Paper"
    ]
    page_reference: int
    document_id: Optional[str] = Field(None, description="Original document identifier")
    
    # --- THE FLATTENED CONTENT ---
    subject: str = Field(
        ..., 
        description="The specific entity, e.g., 'Fiscal Deficit' or 'Repo Rate'"
    )
    predicate: str = Field(
        ..., 
        description="The technical state/action, e.g., 'Targeted reduction' or 'Maintained'"
    )
    value_quantity: Optional[float] = Field(
        None, 
        description="The normalized numerical value for mathematical queries"
    )
    value_unit: Optional[str] = Field(
        None, 
        description="Cr, %, bps, or Currency"
    )
    temporal_context: Optional[str] = Field(
        None,
        description="Time reference: 'FY2025-26', 'Q3 2024', 'Historical 2020-2023'"
    )
    
    # --- NUANCE VECTORS (The 'Sliders') ---
    modality: Literal["Mandatory", "Provisional", "Aspirational", "Historical"] = "Provisional"
    certainty_score: float = Field(
        0.0, 
        ge=0.0, 
        le=1.0, 
        description="1.0 for 'Shall', 0.5 for 'May/Consider', 0.0 for speculative"
    )
    sentiment_magnitude: float = Field(
        0.0, 
        ge=-1.0, 
        le=1.0, 
        description="-1.0 (Hawkish/Contractionary) to +1.0 (Dovish/Expansionary)"
    )
    
    # --- HALLUCINATION MITIGATION (The 'Anchor') ---
    verbatim_extraction: str = Field(
        ..., 
        description="The exact raw text snippet used to derive this fact for verification"
    )
    
    # --- GRAPH LINKAGE ---
    related_entities: List[str] = Field(
        default_factory=list, 
        description="Tags for GraphRAG traversal (e.g., ['Agriculture', 'Infrastructure'])"
    )
    related_facts: List[str] = Field(
        default_factory=list,
        description="IDs of causally or semantically linked facts"
    )
    
    # --- METADATA ---
    extraction_timestamp: datetime = Field(default_factory=datetime.utcnow)
    extraction_model: str = Field(default="gpt-4o-mini", description="Model used for fact extraction")
    confidence_score: float = Field(
        1.0,
        ge=0.0,
        le=1.0,
        description="Extraction confidence from LLM"
    )
    
    class Config:
        frozen = True  # Ensures data integrity once extracted
        json_schema_extra = {
            "example": {
                "fact_id": "f123e4567-e89b-12d3-a456-426614174000",
                "parent_context_id": "f123e4567-e89b-12d3-a456-426614173999",
                "source_origin": "Economic_Survey",
                "page_reference": 42,
                "document_id": "eco_survey_2026_ch3",
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
                "related_facts": [],
                "extraction_model": "gpt-4o-mini",
                "confidence_score": 0.95
            }
        }


class FactExtractionPrompt(BaseModel):
    """Structured prompt for LLM-based fact extraction"""
    
    chunk_text: str
    source_origin: str
    page_reference: int
    document_id: Optional[str] = None
    parent_context_id: Optional[str] = None
    
    system_prompt: str = Field(
        default="""You are a financial document analyst extracting structured facts for a knowledge graph.

EXTRACTION RULES:
1. Break each paragraph into atomic facts (subject-predicate-value triples)
2. Extract numerical values separately with units
3. Capture temporal context (FY, quarter, year)
4. Rate certainty: 1.0 for definitive statements, 0.5 for conditional, 0.0 for speculative
5. Rate sentiment: -1.0 for contractionary/hawkish, 0.0 neutral, +1.0 expansionary/dovish
6. Always include verbatim_extraction for verification
7. Tag entities for graph traversal

OUTPUT: JSON array of RAGIngressFact objects"""
    )


class FactSearchQuery(BaseModel):
    """Query interface for fact-based retrieval"""
    
    query_text: str
    subject_filter: Optional[List[str]] = None
    entity_filter: Optional[List[str]] = None
    temporal_filter: Optional[str] = None
    source_filter: Optional[List[str]] = None
    min_certainty: float = 0.0
    sentiment_range: Optional[tuple[float, float]] = None
    top_k: int = 10


class FactGraph(BaseModel):
    """Represents a connected subgraph of facts"""
    
    root_fact_id: str
    connected_facts: List[RAGIngressFact]
    reasoning_path: List[str] = Field(
        default_factory=list,
        description="Human-readable traversal path through the graph"
    )
    aggregated_confidence: float = Field(
        default=1.0,
        description="Combined confidence of all facts in the subgraph"
    )
