"""
Phase 5: Insights and Summaries Module

Provides insight extraction, summary generation, and semantic search capabilities.
"""

from insights.extractors import InsightExtractor
from insights.generators import SummaryGenerator
from insights.embeddings import EmbeddingService

__all__ = [
    "InsightExtractor",
    "SummaryGenerator",
    "EmbeddingService",
]
