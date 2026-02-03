"""
Firestore Session Management
Stores conversation history and session metadata in Firestore
No PostgreSQL needed - Firebase handles everything
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import firebase_admin
from firebase_admin import credentials, firestore
from app.core.settings import settings
import logging
import json

logger = logging.getLogger(__name__)


class FirestoreSessionService:
    """Manage chat sessions in Firestore
    
    Credential Priority (MOST SECURE FIRST):
    1. Application Default Credentials (ADC) - no keys needed! ✅
       - Cloud Run: Works automatically
       - Local: Run `gcloud auth application-default login`
    2. FIREBASE_CREDENTIALS_JSON environment variable (inline JSON)
    3. FIREBASE_CREDENTIALS_PATH file path (service account file)
    """
    
    def __init__(self):
        """Initialize Firebase Admin SDK (once per process)"""
        self.db = None
        self.sessions_collection = None
        self._initialized = False
        self._credential_type = None  # Track which credential method worked
    
    def _ensure_initialized(self):
        """Lazy initialization of Firebase Admin SDK
        
        Tries credentials in this order (MOST SECURE FIRST):
        1. Application Default Credentials (ADC) - no keys needed! ✅
        2. Inline JSON credentials (FIREBASE_CREDENTIALS_JSON)
        3. Credentials file path (FIREBASE_CREDENTIALS_PATH)
        """
        if self._initialized:
            return
        
        try:
            # Check if already initialized
            if not firebase_admin._apps:
                
                # 1. Try Application Default Credentials FIRST (MOST SECURE) ✅
                # Works on Cloud Run/GCE/GKE automatically
                # For local: run `gcloud auth application-default login`
                try:
                    logger.info("Attempting Application Default Credentials (ADC)...")
                    firebase_admin.initialize_app()
                    logger.info("✅ Firebase Admin initialized with Application Default Credentials (NO KEYS!)")
                    self._credential_type = "ADC"
                
                except Exception as adc_error:
                    logger.warning(f"ADC not available: {adc_error}")
                    
                    # 2. Try inline JSON credentials (for Cloud Run env var)
                    if settings.FIREBASE_CREDENTIALS_JSON:
                        logger.info("Using inline Firebase credentials from FIREBASE_CREDENTIALS_JSON")
                        cred_dict = json.loads(settings.FIREBASE_CREDENTIALS_JSON)
                        cred = credentials.Certificate(cred_dict)
                        firebase_admin.initialize_app(cred)
                        logger.info("✅ Firebase Admin initialized with inline credentials")
                        self._credential_type = "inline"
                    
                    # 3. Try credentials file path (for local development with service account)
                    elif settings.FIREBASE_CREDENTIALS_PATH:
                        logger.info(f"Using Firebase credentials from {settings.FIREBASE_CREDENTIALS_PATH}")
                        cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
                        firebase_admin.initialize_app(cred)
                        logger.info("✅ Firebase Admin initialized with credentials file")
                        self._credential_type = "file"
                    
                    else:
                        raise Exception(
                            "No Firebase credentials available. Options:\n"
                            "1. RECOMMENDED: Use Application Default Credentials:\n"
                            "   Local: Run `gcloud auth application-default login`\n"
                            "   Cloud Run: Automatic (no setup needed)\n"
                            "2. Set FIREBASE_CREDENTIALS_JSON env var (for Cloud Run)\n"
                            "3. Set FIREBASE_CREDENTIALS_PATH to service account JSON file (not recommended)"
                        )
            
            self.db = firestore.client()
            self.sessions_collection = self.db.collection('chat_sessions')
            self._initialized = True
            logger.info(f"🔥 Firestore session service initialized successfully (using {self._credential_type})")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Firestore: {e}")
            logger.warning("⚠️  Sessions will NOT persist (in-memory only)")
            # Don't fail the app - sessions just won't persist
            self._initialized = False
    
    async def get_session(self, session_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session data from Firestore
        Validates that session belongs to user
        
        Args:
            session_id: Unique session identifier
            user_id: Firebase user ID (uid)
            
        Returns:
            Session data dict or None if not found/unauthorized
        """
        try:
            self._ensure_initialized()
            if not self._initialized:
                logger.warning("Firestore not initialized, skipping session load")
                return None
            
            doc_ref = self.sessions_collection.document(session_id)
            doc = doc_ref.get()
            
            if not doc.exists:
                logger.debug(f"Session {session_id} not found")
                return None
            
            data = doc.to_dict()
            
            # Security: Verify ownership
            if data.get('user_id') != user_id:
                logger.warning(f"Session {session_id} access denied for user {user_id}")
                return None
            
            logger.info(f"Session {session_id} loaded for user {user_id}")
            return data
        
        except Exception as e:
            logger.error(f"Error fetching session {session_id}: {e}")
            return None
    
    async def save_session(
        self,
        session_id: str,
        user_id: str,
        conversation_history: List[Dict[str, str]],
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Save or update session in Firestore
        
        Args:
            session_id: Unique session identifier
            user_id: Firebase user ID (uid)
            conversation_history: List of {role, content} dicts
            metadata: Optional metadata (e.g., top_k, model used)
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            self._ensure_initialized()
            if not self._initialized:
                logger.warning("Firestore not initialized, skipping session save")
                return False
            
            doc_ref = self.sessions_collection.document(session_id)
            
            # Limit conversation history to last 20 messages (10 turns)
            # Keeps storage small and responses fast
            trimmed_history = conversation_history[-20:]
            
            session_data = {
                'user_id': user_id,
                'conversation_history': trimmed_history,
                'last_active': firestore.SERVER_TIMESTAMP,
                'message_count': len(conversation_history),
                'metadata': metadata or {}
            }
            
            # Create or update
            doc = doc_ref.get()
            if not doc.exists:
                session_data['created_at'] = firestore.SERVER_TIMESTAMP
                doc_ref.set(session_data)
                logger.info(f"Session {session_id} created for user {user_id}")
            else:
                doc_ref.update(session_data)
                logger.debug(f"Session {session_id} updated")
            
            return True
        
        except Exception as e:
            logger.error(f"Error saving session {session_id}: {e}")
            return False
    
    async def delete_session(self, session_id: str, user_id: str) -> bool:
        """
        Delete session (with ownership check)
        
        Args:
            session_id: Session to delete
            user_id: User requesting deletion
            
        Returns:
            True if deleted, False if not found or unauthorized
        """
        try:
            self._ensure_initialized()
            if not self._initialized:
                return False
            
            doc_ref = self.sessions_collection.document(session_id)
            doc = doc_ref.get()
            
            if not doc.exists:
                return False
            
            data = doc.to_dict()
            
            # Security: Only owner can delete
            if data.get('user_id') != user_id:
                logger.warning(f"Cannot delete session {session_id} - not owned by {user_id}")
                return False
            
            doc_ref.delete()
            logger.info(f"Session {session_id} deleted")
            return True
        
        except Exception as e:
            logger.error(f"Error deleting session {session_id}: {e}")
            return False
    
    async def get_user_sessions(
        self,
        user_id: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get all sessions for a user (for session history UI)
        
        Args:
            user_id: Firebase user ID
            limit: Max number of sessions to return
            
        Returns:
            List of session dicts with metadata
        """
        try:
            self._ensure_initialized()
            if not self._initialized:
                return []
            
            sessions = self.sessions_collection.where(
                'user_id', '==', user_id
            ).order_by(
                'last_active', direction=firestore.Query.DESCENDING
            ).limit(limit).stream()
            
            result = []
            for doc in sessions:
                data = doc.to_dict()
                data['session_id'] = doc.id
                # Don't return full conversation history (too large)
                data.pop('conversation_history', None)
                result.append(data)
            
            logger.info(f"Retrieved {len(result)} sessions for user {user_id}")
            return result
        
        except Exception as e:
            logger.error(f"Error fetching user sessions: {e}")
            return []
    
    async def cleanup_old_sessions(self, days: int = 30) -> int:
        """
        Cleanup sessions older than N days
        Should be run periodically via Cloud Scheduler
        
        Args:
            days: Delete sessions inactive for this many days
            
        Returns:
            Number of sessions deleted
        """
        try:
            self._ensure_initialized()
            if not self._initialized:
                return 0
            
            cutoff = datetime.now() - timedelta(days=days)
            
            # Query old sessions
            old_sessions = self.sessions_collection.where(
                'last_active', '<', cutoff
            ).stream()
            
            count = 0
            for doc in old_sessions:
                doc.reference.delete()
                count += 1
            
            if count > 0:
                logger.info(f"Cleaned up {count} old sessions (older than {days} days)")
            
            return count
        
        except Exception as e:
            logger.error(f"Error cleaning up sessions: {e}")
            return 0


# Global instance
firestore_sessions = FirestoreSessionService()
