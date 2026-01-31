"""
Authentication Service for Google OAuth 2.0

Handles:
- Google ID token verification
- Session token creation and validation
- User authentication
"""

from google.auth.transport.requests import Request
from google.oauth2.id_token import verify_oauth2_token
from datetime import datetime, timedelta
from jose import JWTError, jwt
import os
import logging

logger = logging.getLogger(__name__)


class AuthService:
    """Manage OAuth authentication and session tokens"""
    
    def __init__(self):
        self.client_id = os.getenv("GOOGLE_CLIENT_ID")
        self.secret_key = os.getenv("SESSION_SECRET")
        self.algorithm = "HS256"
        
        if not self.client_id:
            logger.warning("GOOGLE_CLIENT_ID not set - OAuth will fail")
        if not self.secret_key:
            logger.warning("SESSION_SECRET not set - Sessions will fail")
    
    def verify_google_token(self, token: str) -> dict:
        """
        Verify Google ID token signature and validity
        
        Args:
            token: ID token from Google OAuth 2.0
            
        Returns:
            Dictionary with:
            - google_id: User's Google ID
            - email: User's email address
            - name: User's display name
            - picture: User's profile picture URL
            - email_verified: Whether email is verified
            
        Raises:
            ValueError: If token is invalid, expired, or has wrong issuer
        """
        try:
            if not self.client_id:
                raise ValueError("GOOGLE_CLIENT_ID not configured")
            
            # Verify token signature and get claims
            idinfo = verify_oauth2_token(token, Request(), self.client_id)
            
            # Verify issuer (must be Google)
            if idinfo.get('iss') not in ['accounts.google.com', 'https://accounts.google.com']:
                raise ValueError('Invalid token issuer')
            
            logger.info(f"✓ Google token verified for: {idinfo.get('email')}")
            
            # Return user info
            return {
                'google_id': idinfo['sub'],
                'email': idinfo.get('email'),
                'name': idinfo.get('name'),
                'picture': idinfo.get('picture'),
                'email_verified': idinfo.get('email_verified', False)
            }
        
        except ValueError as e:
            logger.error(f"Token verification failed: {str(e)}")
            raise ValueError(f"Invalid Google token: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error verifying token: {str(e)}")
            raise ValueError(f"Token verification error: {str(e)}")
    
    def create_session_token(self, google_id: str, email: str, expires_hours: int = 24) -> dict:
        """
        Create JWT session token for authenticated user
        
        Args:
            google_id: User's Google ID
            email: User's email
            expires_hours: Token expiration in hours (default 24)
            
        Returns:
            Dictionary with:
            - access_token: JWT token
            - token_type: Always 'bearer'
            - expires_in: Seconds until expiration
        """
        try:
            if not self.secret_key:
                raise ValueError("SESSION_SECRET not configured")
            
            # Calculate expiration
            expires_delta = timedelta(hours=expires_hours)
            expire = datetime.utcnow() + expires_delta
            
            # Create payload
            payload = {
                'sub': google_id,      # Subject (user ID)
                'email': email,         # Email
                'exp': expire,          # Expiration time
                'iat': datetime.utcnow() # Issued at
            }
            
            # Sign token
            encoded_jwt = jwt.encode(
                payload,
                self.secret_key,
                algorithm=self.algorithm
            )
            
            logger.info(f"✓ Session token created for: {email}")
            
            return {
                'access_token': encoded_jwt,
                'token_type': 'bearer',
                'expires_in': int(expires_delta.total_seconds())
            }
        
        except Exception as e:
            logger.error(f"Session token creation failed: {str(e)}")
            raise ValueError(f"Could not create session: {str(e)}")
    
    def verify_session_token(self, token: str) -> dict:
        """
        Verify JWT session token and return payload
        
        Args:
            token: JWT session token
            
        Returns:
            Decoded payload with:
            - sub: Google ID
            - email: User email
            - exp: Expiration timestamp
            - iat: Issued at timestamp
            
        Raises:
            ValueError: If token is invalid or expired
        """
        try:
            if not self.secret_key:
                raise ValueError("SESSION_SECRET not configured")
            
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            
            logger.debug(f"✓ Session token verified for: {payload.get('email')}")
            return payload
        
        except JWTError as e:
            logger.error(f"Session token verification failed: {str(e)}")
            raise ValueError(f"Invalid session token: {str(e)}")
        except Exception as e:
            logger.error(f"Token verification error: {str(e)}")
            raise ValueError(f"Token verification error: {str(e)}")
    
    def is_token_expired(self, token: str) -> bool:
        """
        Check if token is expired without verifying signature
        
        Args:
            token: JWT token
            
        Returns:
            True if expired, False otherwise
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={"verify_signature": False}
            )
            
            exp = payload.get('exp')
            if exp and datetime.utcfromtimestamp(exp) < datetime.utcnow():
                return True
            return False
        
        except Exception:
            return True  # Assume expired if can't decode
    
    def get_token_expiration(self, token: str) -> datetime:
        """
        Get token expiration time
        
        Args:
            token: JWT token
            
        Returns:
            Datetime when token expires
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={"verify_signature": False}
            )
            
            exp = payload.get('exp')
            if exp:
                return datetime.utcfromtimestamp(exp)
            return datetime.utcnow()
        
        except Exception:
            return datetime.utcnow()
