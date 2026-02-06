"""
Session Storage Adapter Interface
Abstracts session storage (Firestore, Cosmos DB, Postgres, Redis)
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, List
import os
import logging

logger = logging.getLogger(__name__)


class SessionAdapter(ABC):
    """Base interface for session storage"""
    
    @abstractmethod
    async def get_session(self, session_id: str, user_id: str) -> Optional[Dict]:
        """Get session data"""
        pass
    
    @abstractmethod
    async def save_session(
        self,
        session_id: str,
        user_id: str,
        conversation_history: List[Dict],
        metadata: Optional[Dict] = None
    ) -> bool:
        """Save session data"""
        pass
    
    @abstractmethod
    async def delete_session(self, session_id: str, user_id: str) -> bool:
        """Delete session"""
        pass
    
    @abstractmethod
    def get_storage_name(self) -> str:
        """Return storage name for logging/metrics"""
        pass


class FirestoreSessionAdapter(SessionAdapter):
    """Firestore session storage (GCP default)"""
    
    def __init__(self):
        from app.services.firestore_sessions import firestore_sessions
        self.firestore = firestore_sessions
    
    async def get_session(self, session_id: str, user_id: str) -> Optional[Dict]:
        return await self.firestore.get_session(session_id, user_id)
    
    async def save_session(
        self,
        session_id: str,
        user_id: str,
        conversation_history: List[Dict],
        metadata: Optional[Dict] = None
    ) -> bool:
        return await self.firestore.save_session(
            session_id, user_id, conversation_history, metadata
        )
    
    async def delete_session(self, session_id: str, user_id: str) -> bool:
        return await self.firestore.delete_session(session_id, user_id)
    
    def get_storage_name(self) -> str:
        return "firestore"


class CosmosDBSessionAdapter(SessionAdapter):
    """Azure Cosmos DB session storage (Azure native)"""
    
    def __init__(self):
        self.cosmos_uri = os.getenv('COSMOS_DB_URI')
        self.cosmos_key = os.getenv('COSMOS_DB_KEY')
        self.database_name = os.getenv('COSMOS_DB_NAME', 'rag_sessions')
        self.container_name = 'chat_sessions'
        self._client = None
        self._container = None
        
        if not self.cosmos_uri or not self.cosmos_key:
            logger.warning("Cosmos DB not configured (COSMOS_DB_URI/KEY missing)")
    
    def _get_container(self):
        """Lazy initialization of Cosmos DB client"""
        if self._container is None:
            try:
                from azure.cosmos import CosmosClient
                
                self._client = CosmosClient(self.cosmos_uri, self.cosmos_key)
                database = self._client.get_database_client(self.database_name)
                self._container = database.get_container_client(self.container_name)
            except Exception as e:
                logger.error(f"Cosmos DB initialization failed: {e}")
        return self._container
    
    async def get_session(self, session_id: str, user_id: str) -> Optional[Dict]:
        try:
            container = self._get_container()
            if not container:
                return None
            
            item = container.read_item(
                item=session_id,
                partition_key=user_id
            )
            
            # Verify ownership
            if item.get('user_id') != user_id:
                return None
            
            return item
            
        except Exception as e:
            logger.error(f"Cosmos DB get error: {e}")
            return None
    
    async def save_session(
        self,
        session_id: str,
        user_id: str,
        conversation_history: List[Dict],
        metadata: Optional[Dict] = None
    ) -> bool:
        try:
            container = self._get_container()
            if not container:
                return False
            
            # Trim history
            trimmed_history = conversation_history[-20:]
            
            item = {
                'id': session_id,
                'user_id': user_id,
                'conversation_history': trimmed_history,
                'metadata': metadata or {},
                'message_count': len(conversation_history)
            }
            
            container.upsert_item(item)
            return True
            
        except Exception as e:
            logger.error(f"Cosmos DB save error: {e}")
            return False
    
    async def delete_session(self, session_id: str, user_id: str) -> bool:
        try:
            container = self._get_container()
            if not container:
                return False
            
            container.delete_item(
                item=session_id,
                partition_key=user_id
            )
            return True
            
        except Exception as e:
            logger.error(f"Cosmos DB delete error: {e}")
            return False
    
    def get_storage_name(self) -> str:
        return "cosmosdb"


class PostgresSessionAdapter(SessionAdapter):
    """PostgreSQL session storage (for SQL needs)"""
    
    def __init__(self):
        from app.core.settings import settings
        self.database_url = settings.get_database_url
    
    async def get_session(self, session_id: str, user_id: str) -> Optional[Dict]:
        try:
            from sqlalchemy import text, create_engine
            from sqlalchemy.pool import NullPool
            
            engine = create_engine(self.database_url, poolclass=NullPool)
            
            with engine.connect() as conn:
                result = conn.execute(
                    text("""
                        SELECT conversation_history, metadata, message_count
                        FROM chat_sessions
                        WHERE session_id = :session_id AND user_id = :user_id
                    """),
                    {'session_id': session_id, 'user_id': user_id}
                )
                row = result.fetchone()
                
                if not row:
                    return None
                
                return {
                    'conversation_history': row[0],
                    'metadata': row[1],
                    'message_count': row[2]
                }
                
        except Exception as e:
            logger.error(f"Postgres get error: {e}")
            return None
    
    async def save_session(
        self,
        session_id: str,
        user_id: str,
        conversation_history: List[Dict],
        metadata: Optional[Dict] = None
    ) -> bool:
        try:
            from sqlalchemy import text, create_engine
            from sqlalchemy.pool import NullPool
            import json
            
            engine = create_engine(self.database_url, poolclass=NullPool)
            
            # Trim history
            trimmed_history = conversation_history[-20:]
            
            with engine.connect() as conn:
                conn.execute(
                    text("""
                        INSERT INTO chat_sessions 
                        (session_id, user_id, conversation_history, metadata, message_count, updated_at)
                        VALUES (:session_id, :user_id, :history::jsonb, :metadata::jsonb, :count, NOW())
                        ON CONFLICT (session_id, user_id) 
                        DO UPDATE SET 
                            conversation_history = :history::jsonb,
                            metadata = :metadata::jsonb,
                            message_count = :count,
                            updated_at = NOW()
                    """),
                    {
                        'session_id': session_id,
                        'user_id': user_id,
                        'history': json.dumps(trimmed_history),
                        'metadata': json.dumps(metadata or {}),
                        'count': len(conversation_history)
                    }
                )
                conn.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"Postgres save error: {e}")
            return False
    
    async def delete_session(self, session_id: str, user_id: str) -> bool:
        try:
            from sqlalchemy import text, create_engine
            from sqlalchemy.pool import NullPool
            
            engine = create_engine(self.database_url, poolclass=NullPool)
            
            with engine.connect() as conn:
                conn.execute(
                    text("""
                        DELETE FROM chat_sessions
                        WHERE session_id = :session_id AND user_id = :user_id
                    """),
                    {'session_id': session_id, 'user_id': user_id}
                )
                conn.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"Postgres delete error: {e}")
            return False
    
    def get_storage_name(self) -> str:
        return "postgres"


def get_session_adapter() -> SessionAdapter:
    """
    Get session adapter based on environment config
    Priority: Cosmos DB → Postgres → Firestore (default)
    """
    session_storage = os.getenv('SESSION_STORAGE', 'auto').lower()
    
    if session_storage == 'cosmosdb' or (session_storage == 'auto' and os.getenv('COSMOS_DB_URI')):
        logger.info("Using Cosmos DB session storage")
        return CosmosDBSessionAdapter()
    
    elif session_storage == 'postgres' or (session_storage == 'auto' and os.getenv('DATABASE_URL')):
        logger.info("Using PostgreSQL session storage")
        return PostgresSessionAdapter()
    
    else:
        logger.info("Using Firestore session storage (default)")
        return FirestoreSessionAdapter()
