"""
Redis Session Cache Service
Ultra-fast session management with automatic TTL
"""
import redis
import json
import logging
from typing import Optional, Dict, Any, List
import os

logger = logging.getLogger(__name__)


class RedisSessionCache:
    """
    Redis-based session cache for conversation history
    
    Benefits:
    - Ultra-fast: <1ms latency
    - Automatic expiration (TTL)
    - Scales horizontally
    - Reduces Firestore reads
    """
    
    def __init__(self):
        self.client = None
        self._initialized = False
        self.session_ttl = 3600  # 1 hour
    
    def _ensure_initialized(self):
        """Lazy initialization of Redis client"""
        if self._initialized:
            return
        
        # Check if Redis is configured
        redis_host = os.getenv('REDIS_HOST', None)
        if not redis_host:
            logger.info("Redis not configured (REDIS_HOST not set). Session cache disabled - using Firestore only.")
            self._initialized = False
            self.client = None
            return
        
        try:
            redis_port = int(os.getenv('REDIS_PORT', 6379))
            redis_password = os.getenv('REDIS_PASSWORD', None)
            
            self.client = redis.Redis(
                host=redis_host,
                port=redis_port,
                password=redis_password,
                decode_responses=True,  # Auto-decode bytes to strings
                socket_connect_timeout=2,
                socket_timeout=2,
                retry_on_timeout=True,
                health_check_interval=30
            )
            
            # Test connection
            self.client.ping()
            self._initialized = True
            logger.info(f"Redis connected: {redis_host}:{redis_port}")
            
        except Exception as e:
            logger.warning(f"Redis initialization failed: {e}. Session cache disabled.")
            self._initialized = False
            self.client = None
    
    def _get_key(self, session_id: str, user_id: str) -> str:
        """Generate Redis key with namespace"""
        return f"session:{user_id}:{session_id}"
    
    def get_session(self, session_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session from Redis cache
        
        Returns:
            Session data dict or None if not found/error
        """
        try:
            self._ensure_initialized()
            if not self._initialized or not self.client:
                return None
            
            key = self._get_key(session_id, user_id)
            data = self.client.get(key)
            
            if data:
                session = json.loads(data)
                logger.debug(f"Redis cache HIT: {session_id}")
                return session
            else:
                logger.debug(f"Redis cache MISS: {session_id}")
                return None
                
        except Exception as e:
            logger.warning(f"Redis get error for {session_id}: {e}")
            return None
    
    def set_session(
        self,
        session_id: str,
        user_id: str,
        conversation_history: List[Dict[str, str]],
        metadata: Optional[Dict[str, Any]] = None,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Save session to Redis cache with TTL
        
        Args:
            session_id: Session identifier
            user_id: Firebase user ID
            conversation_history: List of message dicts
            metadata: Optional metadata
            ttl: Time to live in seconds (default: 1 hour)
            
        Returns:
            True if saved, False otherwise
        """
        try:
            self._ensure_initialized()
            if not self._initialized or not self.client:
                return False
            
            key = self._get_key(session_id, user_id)
            
            # Build session data
            session_data = {
                'user_id': user_id,
                'conversation_history': conversation_history,
                'metadata': metadata or {}
            }
            
            # Serialize and save with TTL
            data_json = json.dumps(session_data)
            ttl_seconds = ttl or self.session_ttl
            
            self.client.setex(key, ttl_seconds, data_json)
            logger.debug(f"Redis cache SET: {session_id} (TTL: {ttl_seconds}s)")
            return True
            
        except Exception as e:
            logger.warning(f"Redis set error for {session_id}: {e}")
            return False
    
    def delete_session(self, session_id: str, user_id: str) -> bool:
        """Delete session from Redis cache"""
        try:
            self._ensure_initialized()
            if not self._initialized or not self.client:
                return False
            
            key = self._get_key(session_id, user_id)
            deleted = self.client.delete(key)
            
            if deleted:
                logger.info(f"Redis cache DELETE: {session_id}")
            return deleted > 0
            
        except Exception as e:
            logger.warning(f"Redis delete error for {session_id}: {e}")
            return False
    
    def extend_ttl(self, session_id: str, user_id: str, ttl: Optional[int] = None) -> bool:
        """Extend session TTL (refresh on activity)"""
        try:
            self._ensure_initialized()
            if not self._initialized or not self.client:
                return False
            
            key = self._get_key(session_id, user_id)
            ttl_seconds = ttl or self.session_ttl
            
            # Update expiration time
            extended = self.client.expire(key, ttl_seconds)
            if extended:
                logger.debug(f"Redis TTL extended: {session_id}")
            return extended
            
        except Exception as e:
            logger.warning(f"Redis TTL extend error for {session_id}: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get Redis stats for monitoring"""
        try:
            self._ensure_initialized()
            if not self._initialized or not self.client:
                return {"status": "disconnected"}
            
            info = self.client.info()
            return {
                "status": "connected",
                "used_memory_human": info.get('used_memory_human'),
                "connected_clients": info.get('connected_clients'),
                "total_commands_processed": info.get('total_commands_processed'),
                "keyspace_hits": info.get('keyspace_hits', 0),
                "keyspace_misses": info.get('keyspace_misses', 0),
                "hit_rate": self._calculate_hit_rate(info)
            }
            
        except Exception as e:
            logger.warning(f"Redis stats error: {e}")
            return {"status": "error", "error": str(e)}
    
    def _calculate_hit_rate(self, info: Dict) -> float:
        """Calculate cache hit rate percentage"""
        hits = info.get('keyspace_hits', 0)
        misses = info.get('keyspace_misses', 0)
        total = hits + misses
        
        if total == 0:
            return 0.0
        return round((hits / total) * 100, 2)


# Global instance
redis_cache = RedisSessionCache()
