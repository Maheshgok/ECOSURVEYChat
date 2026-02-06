"""
Feature Flags for A/B Testing and Gradual Rollouts
"""

import os
import logging
from typing import Dict, Any, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class FeatureFlag(Enum):
    """Available feature flags"""
    
    # RAG features
    MULTI_QUERY_RETRIEVAL = "multi_query_retrieval"
    MMR_DIVERSITY = "mmr_diversity"
    QUERY_EXPANSION = "query_expansion"
    CONTEXT_DEDUPLICATION = "context_deduplication"
    
    # Guardrails
    LLM_GUARDRAILS = "llm_guardrails"
    PATTERN_GUARDRAILS = "pattern_guardrails"
    
    # Performance optimizations
    REDIS_CACHE = "redis_cache"
    RESPONSE_STREAMING = "response_streaming"
    
    # Experimental
    HYBRID_SEARCH = "hybrid_search"  # Vector + keyword
    RERANKING = "reranking"  # Cross-encoder reranking


class FeatureFlags:
    """Manage feature flags for A/B testing"""
    
    def __init__(self):
        self._flags: Dict[str, bool] = self._load_defaults()
        self._overrides: Dict[str, float] = {}  # User-specific rollout %
    
    def _load_defaults(self) -> Dict[str, bool]:
        """Load default flag states"""
        defaults = {
            # Core RAG features (enabled by default)
            FeatureFlag.MULTI_QUERY_RETRIEVAL.value: True,
            FeatureFlag.MMR_DIVERSITY.value: True,
            FeatureFlag.QUERY_EXPANSION.value: True,
            FeatureFlag.CONTEXT_DEDUPLICATION.value: True,
            
            # Security (enabled)
            FeatureFlag.PATTERN_GUARDRAILS.value: True,
            FeatureFlag.LLM_GUARDRAILS.value: False,  # Disabled for performance
            
            # Performance (opt-in)
            FeatureFlag.REDIS_CACHE.value: os.getenv('REDIS_HOST') is not None,
            FeatureFlag.RESPONSE_STREAMING.value: False,
            
            # Experimental (opt-in)
            FeatureFlag.HYBRID_SEARCH.value: False,
            FeatureFlag.RERANKING.value: False,
        }
        
        # Override from environment
        for flag in FeatureFlag:
            env_var = f"FEATURE_{flag.value.upper()}"
            if os.getenv(env_var):
                defaults[flag.value] = os.getenv(env_var).lower() in ('true', '1', 'yes')
        
        return defaults
    
    def is_enabled(self, flag: FeatureFlag, user_id: Optional[str] = None) -> bool:
        """
        Check if feature is enabled
        
        Args:
            flag: Feature flag to check
            user_id: Optional user ID for gradual rollout
            
        Returns:
            True if enabled for this user
        """
        # Global flag state
        enabled = self._flags.get(flag.value, False)
        
        # Gradual rollout (if configured)
        if user_id and flag.value in self._overrides:
            rollout_percent = self._overrides[flag.value]
            user_hash = hash(user_id) % 100
            enabled = user_hash < rollout_percent
        
        return enabled
    
    def set_flag(self, flag: FeatureFlag, enabled: bool):
        """Manually set flag state (for testing)"""
        self._flags[flag.value] = enabled
        logger.info(f"Feature flag {flag.value}={enabled}")
    
    def set_rollout(self, flag: FeatureFlag, percent: float):
        """
        Set gradual rollout percentage
        
        Args:
            flag: Feature to roll out
            percent: Percentage of users (0-100)
        """
        if not 0 <= percent <= 100:
            raise ValueError("Rollout percent must be 0-100")
        
        self._overrides[flag.value] = float(percent)
        logger.info(f"Feature rollout {flag.value}={percent}%")
    
    def get_all_flags(self) -> Dict[str, bool]:
        """Get all flag states (for debugging)"""
        return dict(self._flags)


# Global feature flags
_feature_flags = FeatureFlags()


def get_feature_flags() -> FeatureFlags:
    """Get global feature flags instance"""
    return _feature_flags


def is_feature_enabled(flag: FeatureFlag, user_id: Optional[str] = None) -> bool:
    """Check if feature is enabled (convenience function)"""
    return _feature_flags.is_enabled(flag, user_id)
