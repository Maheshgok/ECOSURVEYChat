"""
Firebase Authentication Middleware - Stateless
No database required, validates tokens using public keys
"""
from fastapi import Request, HTTPException, status
from typing import Optional
from app.services.firebase_auth import firebase_service
import logging

logger = logging.getLogger(__name__)


async def get_current_user(request: Request) -> dict:
    """
    Extract and validate Firebase user from Authorization header
    Returns user dict: {uid, email, name, picture, email_verified}
    
    Raises:
        HTTPException: 401 if token is missing, invalid, or expired
    """
    auth_header = request.headers.get('Authorization')
    
    if not auth_header or not auth_header.startswith('Bearer '):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Missing or invalid authorization header',
            headers={'WWW-Authenticate': 'Bearer'}
        )
    
    token = auth_header.replace('Bearer ', '')
    
    try:
        user = await firebase_service.verify_token(token)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Invalid or expired token',
                headers={'WWW-Authenticate': 'Bearer'}
            )
        
        logger.info(f"Authenticated user: {user['email']} (uid: {user['uid']})")
        return user
        
    except Exception as e:
        logger.error(f"Token verification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Token verification failed',
            headers={'WWW-Authenticate': 'Bearer'}
        )


async def get_current_user_optional(request: Request) -> Optional[dict]:
    """
    Same as get_current_user but returns None if not authenticated
    Use for endpoints that work with/without auth
    
    Returns:
        User dict if authenticated, None otherwise
    """
    try:
        return await get_current_user(request)
    except HTTPException:
        return None


def require_auth(user: Optional[dict]) -> dict:
    """
    Helper to enforce authentication in endpoints using optional auth
    
    Args:
        user: Result from get_current_user_optional
        
    Returns:
        User dict
        
    Raises:
        HTTPException: 401 if user is None
    """
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Authentication required',
            headers={'WWW-Authenticate': 'Bearer'}
        )
    return user
