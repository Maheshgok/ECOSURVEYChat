"""
Observability and Metrics Hooks
Provides telemetry, logging, and A/B testing infrastructure
"""

import time
import logging
from typing import Dict, Optional, Any
from functools import wraps
from datetime import datetime
import os

logger = logging.getLogger(__name__)


class Metrics:
    """Centralized metrics collection"""
    
    def __init__(self):
        self.metrics_enabled = os.getenv('ENABLE_METRICS', 'true').lower() == 'true'
        self._metrics_store = []  # In-memory for now, replace with Prometheus/CloudWatch
    
    def record_request(
        self,
        endpoint: str,
        method: str,
        status_code: int,
        duration_ms: float,
        user_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ):
        """Record API request metrics"""
        if not self.metrics_enabled:
            return
        
        metric = {
            'timestamp': datetime.utcnow().isoformat(),
            'type': 'http_request',
            'endpoint': endpoint,
            'method': method,
            'status_code': status_code,
            'duration_ms': duration_ms,
            'user_id': user_id,
            'metadata': metadata or {}
        }
        
        self._metrics_store.append(metric)
        
        # Log slow requests
        if duration_ms > 5000:
            logger.warning(f"Slow request: {endpoint} took {duration_ms:.0f}ms")
    
    def record_rag_query(
        self,
        question: str,
        answer_length: int,
        chunks_retrieved: int,
        duration_ms: float,
        model: str,
        success: bool,
        user_id: Optional[str] = None
    ):
        """Record RAG-specific metrics"""
        if not self.metrics_enabled:
            return
        
        metric = {
            'timestamp': datetime.utcnow().isoformat(),
            'type': 'rag_query',
            'question_length': len(question),
            'answer_length': answer_length,
            'chunks_retrieved': chunks_retrieved,
            'duration_ms': duration_ms,
            'model': model,
            'success': success,
            'user_id': user_id
        }
        
        self._metrics_store.append(metric)
    
    def record_error(
        self,
        error_type: str,
        error_message: str,
        endpoint: Optional[str] = None,
        user_id: Optional[str] = None
    ):
        """Record errors for monitoring"""
        metric = {
            'timestamp': datetime.utcnow().isoformat(),
            'type': 'error',
            'error_type': error_type,
            'error_message': error_message,
            'endpoint': endpoint,
            'user_id': user_id
        }
        
        self._metrics_store.append(metric)
        logger.error(f"Error recorded: {error_type} - {error_message}")
    
    def get_summary(self) -> Dict:
        """Get metrics summary (for health endpoint)"""
        if not self._metrics_store:
            return {'total_events': 0}
        
        total = len(self._metrics_store)
        requests = [m for m in self._metrics_store if m['type'] == 'http_request']
        errors = [m for m in self._metrics_store if m['type'] == 'error']
        
        return {
            'total_events': total,
            'http_requests': len(requests),
            'errors': len(errors),
            'avg_duration_ms': sum(r['duration_ms'] for r in requests) / len(requests) if requests else 0
        }


# Global metrics instance
metrics = Metrics()


def track_request_time(endpoint: str):
    """Decorator to track endpoint timing"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            status_code = 200
            error = None
            
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                status_code = 500
                error = str(e)
                raise
            finally:
                duration_ms = (time.time() - start_time) * 1000
                
                metrics.record_request(
                    endpoint=endpoint,
                    method='POST',  # Most RAG endpoints are POST
                    status_code=status_code,
                    duration_ms=duration_ms,
                    metadata={'error': error} if error else None
                )
        
        return wrapper
    return decorator


class ABTestManager:
    """A/B testing framework for RAG experiments"""
    
    def __init__(self):
        self.enabled = os.getenv('ENABLE_AB_TESTING', 'false').lower() == 'true'
        self.experiments = self._load_experiments()
    
    def _load_experiments(self) -> Dict:
        """Load active experiments from config"""
        # Example experiments configuration
        return {
            'prompt_variant': {
                'variants': ['v1', 'v2'],
                'weights': [0.5, 0.5],
                'description': 'Test different system prompts'
            },
            'retrieval_strategy': {
                'variants': ['mmr', 'similarity'],
                'weights': [0.7, 0.3],
                'description': 'Test retrieval strategies'
            },
            'top_k': {
                'variants': [3, 5, 7],
                'weights': [0.2, 0.6, 0.2],
                'description': 'Test different top_k values'
            }
        }
    
    def get_variant(self, experiment_name: str, user_id: str) -> Any:
        """
        Get variant for user (deterministic based on user_id)
        Ensures consistent experience per user
        """
        if not self.enabled or experiment_name not in self.experiments:
            # Return default (first variant)
            exp = self.experiments.get(experiment_name, {'variants': [None]})
            return exp['variants'][0]
        
        experiment = self.experiments[experiment_name]
        variants = experiment['variants']
        
        # Hash user_id to consistently assign to variant
        import hashlib
        hash_value = int(hashlib.md5(user_id.encode()).hexdigest(), 16)
        variant_idx = hash_value % len(variants)
        
        return variants[variant_idx]
    
    def log_experiment_result(
        self,
        experiment_name: str,
        user_id: str,
        variant: Any,
        outcome: str,
        metadata: Optional[Dict] = None
    ):
        """Log experiment results for analysis"""
        if not self.enabled:
            return
        
        result = {
            'timestamp': datetime.utcnow().isoformat(),
            'experiment': experiment_name,
            'user_id': user_id,
            'variant': variant,
            'outcome': outcome,
            'metadata': metadata or {}
        }
        
        logger.info(f"A/B Test: {experiment_name}={variant}, outcome={outcome}")
        metrics._metrics_store.append({'type': 'ab_test', **result})


# Global A/B test manager
ab_test = ABTestManager()


def with_observability(endpoint_name: str):
    """Combined decorator for metrics and error tracking"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                
                metrics.record_request(
                    endpoint=endpoint_name,
                    method='POST',
                    status_code=200,
                    duration_ms=duration_ms
                )
                
                return result
                
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                
                metrics.record_error(
                    error_type=type(e).__name__,
                    error_message=str(e),
                    endpoint=endpoint_name
                )
                
                metrics.record_request(
                    endpoint=endpoint_name,
                    method='POST',
                    status_code=500,
                    duration_ms=duration_ms
                )
                
                raise
        
        return wrapper
    return decorator
