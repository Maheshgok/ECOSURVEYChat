"""
Simple Firebase Authentication

Routes:
- POST /auth/firebase - Login with Firebase token
- GET /auth/me - Get current user info
"""

from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession
from datetime import datetime
from uuid import UUID
import logging

from app.services.firebase_auth import firebase_service
from app.core.database import get_db
from app.models import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["authentication"])


# Models
class GoogleTokenRequest(BaseModel):
    token: str


class UserResponse(BaseModel):
    id: UUID
    google_id: str
    email: str
    name: str | None
    picture: str | None
    first_login: str | None
    last_login: str | None


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    user: UserResponse


# Dependency
async def get_current_user_dependency(
    req: Request,
    db: DBSession = Depends(get_db)
) -> UserResponse:
    """Validate Firebase token and return current user."""
    try:
        auth_header = req.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="No token provided")
        
        token = auth_header.replace("Bearer ", "")
        firebase_user = await firebase_service.verify_token(token)
        
        if not firebase_user:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        user = db.query(User).filter(User.google_id == firebase_user['uid']).first()
        
        if not user:
            user = User(
                google_id=firebase_user['uid'],
                email=firebase_user['email'],
                name=firebase_user.get('name'),
                picture=firebase_user.get('picture'),
                email_verified=firebase_user.get('email_verified', False)
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        else:
            user.last_login = datetime.utcnow()
            db.commit()
        
        return UserResponse(
            id=user.id,
            google_id=user.google_id,
            email=user.email,
            name=user.name,
            picture=user.picture,
            first_login=user.first_login.isoformat() if user.first_login else None,
            last_login=user.last_login.isoformat() if user.last_login else None
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Auth error: {str(e)}")
        raise HTTPException(status_code=401, detail="Authentication failed")


# Routes
@router.post("/firebase", response_model=LoginResponse)
async def firebase_login(
    request: GoogleTokenRequest,
    db: DBSession = Depends(get_db)
) -> LoginResponse:
    """Authenticate with Firebase token."""
    try:
        firebase_user = await firebase_service.verify_token(request.token)
        if not firebase_user:
            raise HTTPException(status_code=401, detail="Invalid Firebase token")
        
        user = db.query(User).filter(User.google_id == firebase_user['uid']).first()
        
        if not user:
            user = User(
                google_id=firebase_user['uid'],
                email=firebase_user['email'],
                name=firebase_user.get('name'),
                picture=firebase_user.get('picture'),
                email_verified=firebase_user.get('email_verified', False)
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        else:
            user.last_login = datetime.utcnow()
            db.commit()
        
        return LoginResponse(
            access_token=request.token,
            token_type="bearer",
            expires_in=3600,
            user=UserResponse(
                id=user.id,
                google_id=user.google_id,
                email=user.email,
                name=user.name,
                picture=user.picture,
                first_login=user.first_login.isoformat() if user.first_login else None,
                last_login=user.last_login.isoformat() if user.last_login else None
            )
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(status_code=401, detail="Login failed")


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: UserResponse = Depends(get_current_user_dependency)
) -> UserResponse:
    """Get current user info."""
    return current_user
