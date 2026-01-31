"""
Firebase Authentication Service
Handles Firebase token verification and user management
"""

from typing import Optional
import firebase_admin
from firebase_admin import credentials, auth as firebase_auth
from firebase_admin.exceptions import FirebaseError
from app.core.settings import settings
import json
import os


class FirebaseAuthService:
    """Firebase authentication service"""
    
    _initialized = False
    
    @classmethod
    def initialize(cls):
        """Initialize Firebase Admin SDK"""
        if cls._initialized:
            return
        
        try:
            # Try to initialize from credentials path
            if settings.FIREBASE_CREDENTIALS_PATH and os.path.exists(settings.FIREBASE_CREDENTIALS_PATH):
                cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
                firebase_admin.initialize_app(cred)
                cls._initialized = True
                print("✓ Firebase initialized from credentials file")
                return
            
            # Try to initialize from inline JSON
            if settings.FIREBASE_CREDENTIALS_JSON:
                cred_dict = json.loads(settings.FIREBASE_CREDENTIALS_JSON)
                cred = credentials.Certificate(cred_dict)
                firebase_admin.initialize_app(cred)
                cls._initialized = True
                print("✓ Firebase initialized from inline credentials")
                return
            
            # Try to initialize with project ID only (for local emulator)
            if settings.FIREBASE_PROJECT_ID:
                firebase_admin.initialize_app(options={
                    'projectId': settings.FIREBASE_PROJECT_ID
                })
                cls._initialized = True
                print("✓ Firebase initialized with project ID (emulator mode)")
                return
                
            print("⚠ Firebase not configured - auth will not work")
            
        except Exception as e:
            print(f"⚠ Firebase initialization failed: {e}")
    
    @classmethod
    async def verify_token(cls, token: str) -> Optional[dict]:
        """
        Verify Firebase ID token
        
        Args:
            token: Firebase ID token from client
            
        Returns:
            Decoded token dict with user info, or None if invalid
        """
        if not cls._initialized:
            cls.initialize()
        
        if not cls._initialized:
            return None
        
        try:
            # Verify the token
            decoded_token = firebase_auth.verify_id_token(token)
            
            return {
                'uid': decoded_token.get('uid'),
                'email': decoded_token.get('email'),
                'email_verified': decoded_token.get('email_verified', False),
                'name': decoded_token.get('name'),
                'picture': decoded_token.get('picture'),
                'firebase_user': decoded_token
            }
            
        except FirebaseError as e:
            print(f"Firebase token verification failed: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error verifying token: {e}")
            return None
    
    @classmethod
    async def get_user_by_uid(cls, uid: str) -> Optional[dict]:
        """
        Get user info from Firebase by UID
        
        Args:
            uid: Firebase user ID
            
        Returns:
            User info dict or None
        """
        if not cls._initialized:
            cls.initialize()
        
        if not cls._initialized:
            return None
        
        try:
            user = firebase_auth.get_user(uid)
            return {
                'uid': user.uid,
                'email': user.email,
                'email_verified': user.email_verified,
                'display_name': user.display_name,
                'photo_url': user.photo_url,
                'disabled': user.disabled,
            }
        except FirebaseError as e:
            print(f"Error getting Firebase user: {e}")
            return None


# Global instance
firebase_service = FirebaseAuthService()
