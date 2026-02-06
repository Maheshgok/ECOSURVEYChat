"""
Authentication Adapter Interface
Abstracts auth providers (Firebase, Azure AD, custom JWT)
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict
from dataclasses import dataclass
import os
import logging

logger = logging.getLogger(__name__)


@dataclass
class AuthUser:
    """Normalized user data across auth providers"""
    user_id: str  # Unique ID (Firebase uid, Azure oid, etc.)
    email: str
    name: Optional[str] = None
    picture: Optional[str] = None
    email_verified: bool = False
    provider: str = "unknown"  # firebase, azure_ad, custom
    raw_claims: Optional[Dict] = None


class AuthAdapter(ABC):
    """Base interface for authentication providers"""
    
    @abstractmethod
    async def verify_token(self, token: str) -> Optional[AuthUser]:
        """
        Verify authentication token and return user info
        
        Args:
            token: Bearer token from Authorization header
            
        Returns:
            AuthUser if valid, None if invalid/expired
        """
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """Return provider name for logging/metrics"""
        pass


class FirebaseAuthAdapter(AuthAdapter):
    """Firebase Authentication (GCP default)"""
    
    def __init__(self):
        from app.services.firebase_auth import firebase_service
        self.firebase = firebase_service
    
    async def verify_token(self, token: str) -> Optional[AuthUser]:
        try:
            firebase_user = await self.firebase.verify_token(token)
            if not firebase_user:
                return None
            
            return AuthUser(
                user_id=firebase_user['uid'],
                email=firebase_user['email'],
                name=firebase_user.get('name'),
                picture=firebase_user.get('picture'),
                email_verified=firebase_user.get('email_verified', False),
                provider='firebase',
                raw_claims=firebase_user
            )
        except Exception as e:
            logger.error(f"Firebase auth error: {e}")
            return None
    
    def get_provider_name(self) -> str:
        return "firebase"


class AzureADAuthAdapter(AuthAdapter):
    """Azure AD / Microsoft Entra ID (Azure native)"""
    
    def __init__(self):
        self.tenant_id = os.getenv('AZURE_TENANT_ID')
        self.client_id = os.getenv('AZURE_CLIENT_ID')
        
        if not self.tenant_id or not self.client_id:
            logger.warning("Azure AD not configured (AZURE_TENANT_ID/AZURE_CLIENT_ID missing)")
    
    async def verify_token(self, token: str) -> Optional[AuthUser]:
        """
        Verify Azure AD JWT token
        Uses Microsoft's public keys from https://login.microsoftonline.com/{tenant}/discovery/v2.0/keys
        """
        try:
            import jwt
            import requests
            from jwt import PyJWKClient
            
            if not self.tenant_id:
                raise ValueError("AZURE_TENANT_ID not configured")
            
            # Get signing keys from Microsoft
            jwks_uri = f"https://login.microsoftonline.com/{self.tenant_id}/discovery/v2.0/keys"
            jwks_client = PyJWKClient(jwks_uri)
            
            # Get signing key
            signing_key = jwks_client.get_signing_key_from_jwt(token)
            
            # Verify token
            claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=self.client_id,
                issuer=f"https://login.microsoftonline.com/{self.tenant_id}/v2.0"
            )
            
            return AuthUser(
                user_id=claims.get('oid') or claims.get('sub'),  # Azure AD object ID
                email=claims.get('preferred_username') or claims.get('email'),
                name=claims.get('name'),
                picture=None,  # Azure AD doesn't include picture in JWT
                email_verified=True,  # Azure AD pre-verifies
                provider='azure_ad',
                raw_claims=claims
            )
            
        except Exception as e:
            logger.error(f"Azure AD auth error: {e}")
            return None
    
    def get_provider_name(self) -> str:
        return "azure_ad"


class CustomJWTAuthAdapter(AuthAdapter):
    """Custom JWT verification (for private clouds with own IdP)"""
    
    def __init__(self):
        self.secret_key = os.getenv('JWT_SECRET_KEY')
        self.algorithm = os.getenv('JWT_ALGORITHM', 'HS256')
        self.issuer = os.getenv('JWT_ISSUER')
        
        if not self.secret_key:
            logger.warning("Custom JWT not configured (JWT_SECRET_KEY missing)")
    
    async def verify_token(self, token: str) -> Optional[AuthUser]:
        try:
            import jwt
            
            if not self.secret_key:
                raise ValueError("JWT_SECRET_KEY not configured")
            
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                issuer=self.issuer if self.issuer else None
            )
            
            return AuthUser(
                user_id=payload.get('sub') or payload.get('user_id'),
                email=payload.get('email'),
                name=payload.get('name'),
                picture=payload.get('picture'),
                email_verified=payload.get('email_verified', False),
                provider='custom_jwt',
                raw_claims=payload
            )
            
        except Exception as e:
            logger.error(f"Custom JWT auth error: {e}")
            return None
    
    def get_provider_name(self) -> str:
        return "custom_jwt"


# Factory function
def get_auth_adapter() -> AuthAdapter:
    """
    Get auth adapter based on environment config
    Priority: AZURE_TENANT_ID → JWT_SECRET_KEY → Firebase (default)
    """
    auth_provider = os.getenv('AUTH_PROVIDER', 'auto').lower()
    
    if auth_provider == 'azure_ad' or (auth_provider == 'auto' and os.getenv('AZURE_TENANT_ID')):
        logger.info("Using Azure AD authentication")
        return AzureADAuthAdapter()
    
    elif auth_provider == 'custom_jwt' or (auth_provider == 'auto' and os.getenv('JWT_SECRET_KEY')):
        logger.info("Using custom JWT authentication")
        return CustomJWTAuthAdapter()
    
    else:
        logger.info("Using Firebase authentication (default)")
        return FirebaseAuthAdapter()
