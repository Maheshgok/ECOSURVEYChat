"""
Observability Module - Metrics, Logging, and Telemetry
Supports: Prometheus, OpenTelemetry, Azure Monitor, Cloud Monitoring
"""

import time
import logging
from typing import Dict, Any, Optional, Callable
from functools import wraps
from dataclasses import dataclass, field
from datetime import datetime
import json

logger = logging.getLogger(__name__)


@dataclass
class Metric:
    """Single metric data point"""
    name: str
    value: float
    timestamp: float = field(default_factory=time.time)
    labels: Dict[str, str] = field(default_factory=dict)
    unit: str = "count"


class MetricsCollector:
    """Collects and exports metrics for monitoring"""
    
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self._metrics: Dict[str, list] = {}
        self._counters: Dict[str, float] = {}
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, list] = {}
    
    def counter(self, name: str, value: float =, labels: Optional[Dict] = None):
        """Increment counter metric"""
        if not self.enabled:
            return
        
        key = self._make_key(name, labels)
        self._counters[key] = self._counters.get(key, 0) + value
        logger.debug(f"Counter {name}={self._counters[key]} labels={labels}")
    
    def gauge(self, name: str, value: float, labels: Optional[Dict] = None):
        """Set gauge metric (current value)"""
        if not self.enabled:
            return
        
        key = self._make_key(name, labels)
        self._gauges[key] = value
        logger.debug(f"Gauge {name}={value} labels={labels}")
    
    def histogram(self, name: str, value: float, labels: Optional[Dict] = None):
        """Record histogram value (for latency, size distributions)"""
        if not self.enabled:
            return
        
        key = self._make_key(name, labels)
        if key not in self._histograms:
            self._histograms[key] = []
        self._histograms[key].append(value)
        logger.debug(f"Histogram {name} recorded {value} labels={labels}")
    
    def _make_key(self, name: str, labels: Optional[Dict]) -> str:
        """Create unique key from name and labels"""
        if not labels:
            return name
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"
    
    def get_stats(self) -> Dict[str, Any]:
        """Get all collected metrics"""
        return {
            'counters': dict(self._counters),
            'gauges': dict(self._gauges),
            'histograms': {
                k: {
                    'count': len(v),
                    'min': min(v) if v else 0,
                    'max': max(v) if v else 0,
                    'avg': sum(v) / len(v) if v else 0,
                }
                for k, v in self._histograms.items()
            }
        }
    
    def reset(self):
        """Reset all metrics (useful for testing)"""        
        self._counters.clear()
        self._gauges.clear()
        self._histograms.clear()


# Global metrics collector
_metrics = MetricsCollector()


def get_metrics() -> MetricsCollector:
    """Get global metrics collector"""
    return _metrics


def track_latency(metric_name: str, labels: Optional[Dict] = None):
    """Decorator to track function latency"""
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start
                _metrics.histogram(metric_name, duration * 1000, labels)  # ms
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start
                _metrics.histogram(metric_name, duration * 1000, labels)  # ms
        
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


def track_requests(endpoint: str):
    """Decorator to track API requests"""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            _metrics.counter('api_requests_total', 1, {'endpoint': endpoint})
            
            start = time.time()
            status = 'success'
            
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                status = 'error'
                _metrics.counter('api_errors_total', 1, {
                    'endpoint': endpoint,
                    'error_type': type(e).__name__
                })
                raise
            finally:
                latency = (time.time() - start) * 1000
                _metrics.histogram('api_latency_ms', latency, {
                    'endpoint': endpoint,
                    'status': status
                })
        
        return wrapper
    return decorator


# Standard metrics for RAG system
def track_rag_query(
    query_length: int,
    chunks_retrieved: int,
    context_tokens: int,
    response_tokens: int,
    total_latency_ms: float,
    cache_hit: bool = False
):
    """Track RAG-specific metrics"""
    labels = {'cache_hit': str(cache_hit)}
    
    _metrics.counter('rag_queries_total', 1, labels)
    _metrics.histogram('rag_query_length', query_length, labels)
    _metrics.histogram('rag_chunks_retrieved', chunks_retrieved, labels)
    _metrics.histogram('rag_context_tokens', context_tokens, labels)
    _metrics.histogram('rag_response_tokens', response_tokens, labels)
    _metrics.histogram('rag_total_latency_ms', total_latency_ms, labels)
    
    # Cost estimation (rough)
    input_cost = context_tokens * 0.00001  # $0.01 per 1K tokens
    output_cost = response_tokens * 0.00003  # $0.03 per 1K tokens
    _metrics.histogram('rag_estimated_cost_usd', input_cost + output_cost, labels)


def track_auth_event(provider: str, success: bool, latency_ms: float):
    """Track authentication events"""
    _metrics.counter('auth_attempts_total', 1, {
        'provider': provider,
        'success': str(success)
    })
    _metrics.histogram('auth_latency_ms', latency_ms, {'provider': provider})
