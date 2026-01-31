"""
Authentication Endpoints for Google OAuth 2.0 and Firebase

Routes:
- POST /auth/google - Authenticate with Google ID token (legacy)
- POST /auth/firebase - Authenticate with Firebase ID token
- POST /auth/logout - Invalidate session
- GET /auth/me - Get current user info
"""

from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession
from datetime import datetime, timedelta
import logging

from app.services.auth_service import AuthService
from app.services.firebase_auth import firebase_service
from app.core.database import get_db
from app.core.settings import settings
from app.models import User, Session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["authentication"])
auth_service = AuthService()


# Request/Response models
class GoogleTokenRequest(BaseModel):
    """Request body for Google OAuth authentication"""
    token: str


class UserResponse(BaseModel):
    """User information response"""
    id: int
    email: str
    name: str | None
    picture: str | None
    first_login: str | None
    last_login: str | None


class LoginResponse(BaseModel):
    """Response from successful login"""
    access_token: str
    token_type: str
    expires_in: int
    user: UserResponse


class LogoutResponse(BaseModel):
    """Response from logout"""
    message: str


# ============================================================================
# Dependency Functions (for protecting routes)
# ============================================================================

async def get_current_user_dependency(
    req: Request,
    db: DBSession = Depends(get_db)
) -> UserResponse:
    """
    Dependency function to get current authenticated user.
    Supports both Firebase tokens and legacy session tokens.
    
    Usage:
        @router.post("/protected")
        async def protected_route(
            current_user: UserResponse = Depends(get_current_user_dependency)
        ):
            return {"user_id": current_user.id}
    """
    # Handle test mode
    if settings.SKIP_AUTH_FOR_TESTING:
        test_user = db.query(User).filter(User.google_id == "test_google_sub").first()
        if test_user:
            return UserResponse(
                id=str(test_user.id),
                email=test_user.email,
                name=test_user.name or test_user.email.split('@')[0],
                picture=test_user.picture,
                first_login=test_user.first_login.isoformat() if test_user.first_login else None,
                last_login=test_user.last_login.isoformat() if test_user.last_login else None
            )
    
    try:
        # Extract token
        auth_header = req.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=401,
                detail="No token provided"
            )
        
        token = auth_header.replace("Bearer ", "")
        
        # Try Firebase token verification first
        firebase_user = await firebase_service.verify_token(token)
        
        if firebase_user:
            # Firebase token valid - get or create user
            user = db.query(User).filter(
                User.google_id == firebase_user['uid']
            ).first()
            
            if not user:
                # Auto-create user from Firebase
                user = User(
                    google_id=firebase_user['uid'],
                    email=firebase_user['email'],
                    name=firebase_user.get('name'),
                    picture=firebase_user.get('picture'),
                    email_verified=firebase_user.get('email_verified', False),
                    first_login=datetime.utcnow(),
                    last_login=datetime.utcnow()
                )
                db.add(user)
                db.commit()
                db.refresh(user)
            else:
                # Update last login
                user.last_login = datetime.utcnow()
                db.commit()
            
            return UserResponse(
                id=str(user.id),
                email=user.email,
                name=user.name or user.email.split('@')[0],
                picture=user.picture,
                first_login=user.first_login.isoformat() if user.first_login else None,
                last_login=user.last_login.isoformat() if user.last_login else None
            )
        
        # Fall back to legacy session token verification
        payload = auth_service.verify_session_token(token)
        
        # Get user from database
        user = db.query(User).filter(
            User.google_id == payload['sub']
        ).first()
        
        if not user:
            raise HTTPException(
                status_code=401,
                detail="User not found"
            )
        
        # Check if session is still active
        session = db.query(Session).filter(
            Session.token == token,
            Session.is_active == True
        ).first()
        
        if not session:
            raise HTTPException(
                status_code=401,
                detail="Session expired or invalid"
            )
        
        # Update last activity
        session.last_activity = datetime.utcnow()
        db.commit()
        
        return UserResponse(
            id=str(user.id),
            email=user.email,
            name=user.name or user.email.split('@')[0],
            picture=user.picture,
            first_login=user.first_login.isoformat() if user.first_login else None,
            last_login=user.last_login.isoformat() if user.last_login else None
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get user error: {str(e)}")
        raise HTTPException(
            status_code=401,
            detail="Invalid token"
        )


# Routes

@router.post("/firebase", response_model=LoginResponse)
async def firebase_login(
    request: GoogleTokenRequest,
    req: Request,
    db: DBSession = Depends(get_db)
) -> LoginResponse:
    """
    Authenticate user with Firebase ID token
    
    **Flow:**
    1. Verify Firebase ID token
    2. Extract user information from token
    3. Create or update user in database
    4. Return Firebase token (client manages it)
    
    This is the preferred production authentication method.
    """
    try:
        # Verify Firebase token
        firebase_user = await firebase_service.verify_token(request.token)
        
        if not firebase_user:
            raise HTTPException(
                status_code=401,
                detail="Invalid Firebase token"
            )
        
        # Get or create user
        user = db.query(User).filter(
            User.google_id == firebase_user['uid']
        ).first()
        
        now = datetime.utcnow()
        
        if not user:
            # Create new user
            user = User(
                google_id=firebase_user['uid'],
                email=firebase_user['email'],
                name=firebase_user.get('name'),
                picture=firebase_user.get('picture'),
                email_verified=firebase_user.get('email_verified', False),
                first_login=now,
                last_login=now,
                is_active=True
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            logger.info(f"New user created via Firebase: {user.email}")
        else:
            # Update existing user
            user.last_login = now
            user.name = firebase_user.get('name') or user.name
            user.picture = firebase_user.get('picture') or user.picture
            db.commit()
            logger.info(f"User logged in via Firebase: {user.email}")
        
        # Return the Firebase token directly - client manages it
        return LoginResponse(
            access_token=request.token,
            token_type="bearer",
            expires_in=3600,  # Firebase tokens are valid for 1 hour
            user=UserResponse(
                id=str(user.id),
                email=user.email,
                name=user.name or user.email.split('@')[0],
                picture=user.picture,
                first_login=user.first_login.isoformat() if user.first_login else None,
                last_login=user.last_login.isoformat() if user.last_login else None
            )
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Firebase login error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Authentication failed"
        )


@router.post("/google", response_model=LoginResponse)
async def google_login(
    request: GoogleTokenRequest,
    req: Request,
    db: DBSession = Depends(get_db)
) -> LoginResponse:
    """
    Authenticate user with Google ID token (LEGACY)
    
    **Flow:**
    1. Verify Google ID token signature
    2. Extract user information (email, name, picture)
    3. Create or update user in database
    4. Create session token
    5. Store session in database
    6. Return session token to client
    
    **Request:**
    ```json
    {
        "token": "google_id_token_from_google_oauth"
    }
    ```
    
    **Response on Success (200):**
    ```json
    {
        "access_token": "jwt_session_token",
        "token_type": "bearer",
        "expires_in": 86400,
        "user": {
            "id": 1,
            "email": "user@example.com",
            "name": "User Name",
            "picture": "https://...",
            "first_login": "2026-01-31T...",
            "last_login": "2026-01-31T..."
        }
    }
    ```
    
    **Response on Failure (401):**
    ```json
    {"detail": "Invalid Google token"}
    ```
    """
    try:
        # Step 1: Verify Google ID token
        logger.info("Verifying Google ID token...")
        user_info = auth_service.verify_google_token(request.token)
        logger.info(f"✓ Google token verified for: {user_info['email']}")
        
        # Step 2: Get or create user in database
        user = db.query(User).filter(
            User.google_id == user_info['google_id']
        ).first()
        
        if not user:
            # New user - create account
            logger.info(f"Creating new user: {user_info['email']}")
            user = User(
                google_id=user_info['google_id'],
                email=user_info['email'],
                name=user_info.get('name'),
                picture=user_info.get('picture'),
                email_verified=user_info.get('email_verified', False),
                first_login=datetime.utcnow(),
                last_login=datetime.utcnow()
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            logger.info(f"✓ New user created: {user.id}")
        else:
            # Existing user - update last login
            logger.info(f"Existing user found: {user.email}")
            user.last_login = datetime.utcnow()
            db.commit()
        
        # Step 3: Create session token
        logger.info(f"Creating session token for user: {user.id}")
        token_response = auth_service.create_session_token(
            google_id=user.google_id,
            email=user.email
        )
        
        # Step 4: Store session in database
        client_ip = req.client.host if req.client else "unknown"
        user_agent = req.headers.get("user-agent", "unknown")
        
        session = Session(
            user_id=user.id,
            token=token_response['access_token'],
            ip_address=client_ip,
            user_agent=user_agent,
            expires_at=datetime.utcnow() + timedelta(hours=24),
            is_active=True
        )
        db.add(session)
        db.commit()
        logger.info(f"✓ Session created for user: {user.id}")
        
        # Step 5: Return response
        return LoginResponse(
            access_token=token_response['access_token'],
            token_type='bearer',
            expires_in=token_response['expires_in'],
            user=UserResponse(
                id=user.id,
                email=user.email,
                name=user.name,
                picture=user.picture,
                first_login=user.first_login.isoformat() if user.first_login else None,
                last_login=user.last_login.isoformat() if user.last_login else None
            )
        )
    
    except ValueError as e:
        logger.error(f"Authentication error: {str(e)}")
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in google_login: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Authentication failed"
        )


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    req: Request,
    db: DBSession = Depends(get_db)
) -> LogoutResponse:
    """
    Logout user by invalidating session
    
    **Request:**
    ```
    Authorization: Bearer <session_token>
    ```
    
    **Response on Success (200):**
    ```json
    {"message": "Logged out successfully"}
    ```
    
    **Response on Failure (401):**
    ```json
    {"detail": "No token provided"}
    ```
    """
    try:
        # Extract token from Authorization header
        auth_header = req.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=401,
                detail="No token provided"
            )
        
        token = auth_header.replace("Bearer ", "")
        
        # Find session and deactivate
        session = db.query(Session).filter(
            Session.token == token,
            Session.is_active == True
        ).first()
        
        if not session:
            raise HTTPException(
                status_code=401,
                detail="Session not found or already expired"
            )
        
        # Deactivate session
        session.is_active = False
        db.commit()
        
        logger.info(f"✓ User {session.user_id} logged out")
        return LogoutResponse(message="Logged out successfully")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Logout failed"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    req: Request,
    db: DBSession = Depends(get_db)
) -> UserResponse:
    """
    Get current authenticated user information
    
    **Request:**
    ```
    Authorization: Bearer <session_token>
    ```
    
    **Response on Success (200):**
    ```json
    {
        "id": 1,
        "email": "user@example.com",
        "name": "User Name",
        "picture": "https://...",
        "first_login": "2026-01-31T...",
        "last_login": "2026-01-31T..."
    }
    ```
    
    **Response on Failure (401):**
    ```json
    {"detail": "Invalid token"}
    ```
    """
    try:
        # Extract token
        auth_header = req.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=401,
                detail="No token provided"
            )
        
        token = auth_header.replace("Bearer ", "")
        
        # Verify session token
        payload = auth_service.verify_session_token(token)
        
        # Get user from database
        user = db.query(User).filter(
            User.google_id == payload['sub']
        ).first()
        
        if not user:
            raise HTTPException(
                status_code=401,
                detail="User not found"
            )
        
        # Check if session is still active
        session = db.query(Session).filter(
            Session.token == token,
            Session.is_active == True
        ).first()
        
        if not session:
            raise HTTPException(
                status_code=401,
                detail="Session expired or invalid"
            )
        
        # Update last activity
        session.last_activity = datetime.utcnow()
        db.commit()
        
        return UserResponse(
            id=user.id,
            email=user.email,
            name=user.name,
            picture=user.picture,
            first_login=user.first_login.isoformat() if user.first_login else None,
            last_login=user.last_login.isoformat() if user.last_login else None
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get user error: {str(e)}")
        raise HTTPException(
            status_code=401,
            detail="Invalid token"
        )
