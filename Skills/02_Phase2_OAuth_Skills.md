# Phase 2: Google OAuth Authentication Skills

**Phase Duration:** 2-3 hours  
**Difficulty:** Medium  
**Prerequisites:** Phase 1 Complete + Google Cloud Account  
**Objective:** Implement secure user authentication via Google OAuth 2.0

---

## Table of Contents

1. [OAuth 2.0 Concepts](#oauth-20-concepts)
2. [Google Cloud Setup](#google-cloud-setup)
3. [Backend Implementation](#backend-implementation)
4. [Session Management](#session-management)
5. [Testing & Validation](#testing--validation)
6. [Security Considerations](#security-considerations)

---

## OAuth 2.0 Concepts

### What is OAuth 2.0?

OAuth 2.0 is an authorization framework that enables users to log in using their Google account without sharing passwords.

**Flow (Authorization Code):**

```
┌─────────────┐                                  ┌──────────────┐
│   Browser   │                                  │ Google OAuth │
│  (Frontend) │                                  │   Server     │
└──────┬──────┘                                  └──────┬───────┘
       │                                                 │
       │  1. Click "Login with Google"                 │
       │  (redirect to Google)                         │
       │────────────────────────────────────────────→  │
       │                                                 │
       │  2. User enters Google credentials            │
       │  Google validates                             │
       │  ←──────────────────────────────────────────  │
       │  (redirect to app with authorization code)    │
       │                                                 │
┌──────┴──────┐              ┌──────────────┐         │
│   Backend   │              │   Backend    │         │
│  (FastAPI)  │              │  (FastAPI)   │         │
└──────┬──────┘              └──────┬───────┘         │
       │                             │                 │
       │  3. POST /auth/google       │                 │
       │     {authorization_code}    │                 │
       │←────────────────────────────│                 │
       │                             │                 │
       │                      4. POST to Google         │
       │                      (code + client_secret)    │
       │                      ←────────────────────────→
       │                      (returns access_token)   │
       │                                               │
       │                      5. Validate & create session
       │                      Return session token to frontend
       │────────────────────────────────────────→      │
       │                                               │
       └───────────────────────────────────────────────┘
```

### Key Terms

- **Authorization Code:** One-time code returned by Google
- **Access Token:** Token proving user is authenticated
- **Session Token:** Token your app gives to user for future requests
- **Client ID/Secret:** Your app's credentials with Google

---

## Google Cloud Setup

### Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create new project: "econsurvey-chat"
3. Enable these APIs:
   - Google+ API
   - Gmail API (optional for Phase 2)

### Step 2: Create OAuth 2.0 Credentials

```
Google Cloud Console > Credentials > Create Credentials > OAuth Client ID

Application Type: Web Application

Authorized JavaScript Origins:
  - http://localhost:3000
  - http://localhost:8000
  - https://yourdomain.com (for production)

Authorized redirect URIs:
  - http://localhost:8000/auth/google/callback
  - http://localhost:3000/auth/callback (for frontend)
  - https://yourdomain.com/auth/google/callback
```

### Step 3: Save Credentials

You'll receive:
- **Client ID:** (looks like: 123456789.apps.googleusercontent.com)
- **Client Secret:** (keep this SECRET!)

**Add to .env:**
```env
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback
```

---

## Backend Implementation

### Step 1: Install Dependencies

```powershell
cd backend
pip install google-auth-oauthlib google-auth-httplib2 google-auth
pip install python-jose python-multipart
pip install secrets
```

Update `backend/requirements.txt`:
```
google-auth-oauthlib==1.1.0
google-auth==2.25.2
python-jose[cryptography]==3.3.0
python-multipart==0.0.6
```

### Step 2: Create OAuth Service

Create `backend/app/services/auth_service.py`:

```python
from google.auth.transport.requests import Request
from google.oauth2.id_token import verify_oauth2_token
from datetime import datetime, timedelta
from jose import JWTError, jwt
import os

class AuthService:
    """Handle OAuth authentication and session management"""
    
    def __init__(self):
        self.client_id = os.getenv("GOOGLE_CLIENT_ID")
        self.secret_key = os.getenv("SESSION_SECRET")
        self.algorithm = "HS256"
    
    def verify_google_token(self, token: str) -> dict:
        """
        Verify Google ID token
        
        Args:
            token: ID token from Google
            
        Returns:
            User info (sub, email, name, picture)
            
        Raises:
            ValueError: If token is invalid
        """
        try:
            # Verify token signature and expiration
            idinfo = verify_oauth2_token(token, Request(), self.client_id)
            
            if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                raise ValueError('Wrong issuer.')
            
            # Token is valid
            return {
                'google_id': idinfo['sub'],
                'email': idinfo.get('email'),
                'name': idinfo.get('name'),
                'picture': idinfo.get('picture'),
                'email_verified': idinfo.get('email_verified', False)
            }
        except ValueError as e:
            raise ValueError(f"Invalid token: {str(e)}")
    
    def create_session_token(self, google_id: str, email: str) -> dict:
        """
        Create session token for the user
        
        Returns:
            {
                'access_token': token,
                'token_type': 'bearer',
                'expires_in': seconds
            }
        """
        # Session valid for 24 hours
        expires_delta = timedelta(hours=24)
        expire = datetime.utcnow() + expires_delta
        
        payload = {
            'sub': google_id,
            'email': email,
            'exp': expire,
            'iat': datetime.utcnow()
        }
        
        encoded_jwt = jwt.encode(
            payload,
            self.secret_key,
            algorithm=self.algorithm
        )
        
        return {
            'access_token': encoded_jwt,
            'token_type': 'bearer',
            'expires_in': int(expires_delta.total_seconds())
        }
    
    def verify_session_token(self, token: str) -> dict:
        """
        Verify and decode session token
        
        Returns:
            Decoded payload with user info
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            return payload
        except JWTError:
            raise ValueError("Invalid session token")
```

### Step 3: Create User Model

Update `backend/app/models/__init__.py`:

```python
class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    google_id = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255))
    picture = Column(String(500))
    email_verified = Column(Boolean, default=False)
    
    # Account tracking
    first_login = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    sessions = relationship("Session", back_populates="user")
    conversations = relationship("Conversation", back_populates="user")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

### Step 4: Create Session Model

Add to `backend/app/models/__init__.py`:

```python
class Session(Base):
    __tablename__ = 'sessions'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    token = Column(String(500), unique=True, nullable=False, index=True)
    
    # Session tracking
    ip_address = Column(String(45))  # IPv4 or IPv6
    user_agent = Column(String(500))
    
    # Expiration
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    last_activity = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Relationships
    user = relationship("User", back_populates="sessions")
```

### Step 5: Implement OAuth Routes

Update `backend/app/api/auth.py`:

```python
from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession
from app.services.auth_service import AuthService
from app.core.database import SessionLocal
from app.models import User, Session
import logging

router = APIRouter(prefix="/auth", tags=["authentication"])
auth_service = AuthService()
logger = logging.getLogger(__name__)

class GoogleTokenRequest(BaseModel):
    token: str  # ID token from Google

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: dict

@router.post("/google", response_model=LoginResponse)
async def google_login(request: GoogleTokenRequest, req: Request, db: DBSession = Depends(SessionLocal)):
    """
    Authenticate with Google ID token
    
    Flow:
    1. Verify Google ID token signature
    2. Extract user info (email, name, picture)
    3. Create or update user in database
    4. Create session token
    5. Return session token to frontend
    """
    try:
        # Step 1: Verify Google token
        logger.info("Verifying Google token...")
        user_info = auth_service.verify_google_token(request.token)
        logger.info(f"Google token verified for: {user_info['email']}")
        
        # Step 2: Get or create user
        user = db.query(User).filter(User.google_id == user_info['google_id']).first()
        
        if not user:
            logger.info(f"Creating new user: {user_info['email']}")
            user = User(
                google_id=user_info['google_id'],
                email=user_info['email'],
                name=user_info.get('name'),
                picture=user_info.get('picture'),
                email_verified=user_info.get('email_verified', False)
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        else:
            logger.info(f"User exists: {user_info['email']}")
            # Update last login
            user.last_login = datetime.utcnow()
            db.commit()
        
        # Step 3: Create session token
        logger.info(f"Creating session token for user: {user.id}")
        token_response = auth_service.create_session_token(user.google_id, user.email)
        
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
        
        # Step 5: Return response
        return LoginResponse(
            access_token=token_response['access_token'],
            token_type='bearer',
            user={
                'id': user.id,
                'email': user.email,
                'name': user.name,
                'picture': user.picture,
                'first_login': user.first_login.isoformat() if user.first_login else None
            }
        )
    
    except ValueError as e:
        logger.error(f"Authentication error: {str(e)}")
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in google_login: {str(e)}")
        raise HTTPException(status_code=500, detail="Authentication failed")

@router.post("/logout")
async def logout(req: Request, db: DBSession = Depends(SessionLocal)):
    """
    Logout user (invalidate session)
    
    Expects:
    Authorization: Bearer <token>
    """
    token = req.headers.get("Authorization", "").replace("Bearer ", "")
    
    if not token:
        raise HTTPException(status_code=401, detail="No token provided")
    
    try:
        # Find and deactivate session
        session = db.query(Session).filter(Session.token == token).first()
        
        if not session:
            raise HTTPException(status_code=401, detail="Session not found")
        
        session.is_active = False
        db.commit()
        
        logger.info(f"User {session.user_id} logged out")
        return {"message": "Logged out successfully"}
    
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        raise HTTPException(status_code=500, detail="Logout failed")

@router.get("/me")
async def get_current_user(req: Request, db: DBSession = Depends(SessionLocal)):
    """
    Get current authenticated user info
    
    Expects:
    Authorization: Bearer <token>
    """
    token = req.headers.get("Authorization", "").replace("Bearer ", "")
    
    if not token:
        raise HTTPException(status_code=401, detail="No token provided")
    
    try:
        # Verify session token
        payload = auth_service.verify_session_token(token)
        
        # Get user from database
        user = db.query(User).filter(User.google_id == payload['sub']).first()
        
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        
        return {
            'id': user.id,
            'email': user.email,
            'name': user.name,
            'picture': user.picture,
            'first_login': user.first_login.isoformat() if user.first_login else None,
            'last_login': user.last_login.isoformat() if user.last_login else None
        }
    
    except Exception as e:
        logger.error(f"Get user error: {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid token")
```

### Step 6: Add Session Dependency

Create `backend/app/core/dependencies.py`:

```python
from fastapi import Depends, HTTPException, Request
from app.services.auth_service import AuthService
from sqlalchemy.orm import Session as DBSession
from app.core.database import SessionLocal
from app.models import User, Session as SessionModel

auth_service = AuthService()

async def get_current_user(
    request: Request,
    db: DBSession = Depends(SessionLocal)
) -> User:
    """
    Dependency to get current authenticated user
    
    Usage:
        @router.get("/protected")
        def protected_route(user: User = Depends(get_current_user)):
            return {"message": f"Hello {user.name}"}
    """
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    
    if not token:
        raise HTTPException(status_code=401, detail="No token provided")
    
    try:
        # Verify token
        payload = auth_service.verify_session_token(token)
        
        # Get user
        user = db.query(User).filter(User.google_id == payload['sub']).first()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        
        # Check if session is still active
        session = db.query(SessionModel).filter(
            SessionModel.token == token,
            SessionModel.is_active == True
        ).first()
        
        if not session:
            raise HTTPException(status_code=401, detail="Session invalid or expired")
        
        # Update last activity
        from datetime import datetime
        session.last_activity = datetime.utcnow()
        db.commit()
        
        return user
    
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid token")
```

### Step 7: Update Main App

Update `backend/app/main.py` to include auth routes:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import health, auth
from app.core.database import init_db
import logging

app = FastAPI(
    title="Economic Survey Chat",
    version="1.2",
    description="Practitioner-focused economic data chat interface"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router)
app.include_router(auth.router)

@app.on_event("startup")
async def startup_event():
    logger.info("Starting Economic Survey Chat v1.2")
    try:
        init_db()
    except Exception as e:
        logger.error(f"Database init failed: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

---

## Session Management

### Token Expiration Strategy

```python
# Session expires after 24 hours
EXPIRES_IN = 24  # hours

# Refresh token available for 30 days
REFRESH_EXPIRES_IN = 30  # days

# Absolute maximum session: 7 days (even with refresh)
MAX_SESSION_AGE = 7  # days
```

### Session Invalidation

Sessions are invalidated when:
1. User clicks logout (set `is_active = False`)
2. Token expires (check `expires_at`)
3. Suspicious activity (IP change, user agent change)
4. User changes password (not Phase 2, but future reference)

### Cleanup Old Sessions

Create `backend/app/services/session_service.py`:

```python
from datetime import datetime, timedelta
from sqlalchemy.orm import Session as DBSession
from app.models import Session

def cleanup_expired_sessions(db: DBSession):
    """Remove expired sessions from database"""
    now = datetime.utcnow()
    
    expired = db.query(Session).filter(Session.expires_at < now).delete()
    inactive = db.query(Session).filter(Session.is_active == False).filter(
        Session.updated_at < now - timedelta(days=7)
    ).delete()
    
    db.commit()
    return expired + inactive
```

---

## Testing & Validation

### Unit Tests

Create `backend/tests/test_auth.py`:

```python
import pytest
from app.services.auth_service import AuthService
from datetime import datetime, timedelta

def test_create_session_token():
    """Test session token creation"""
    auth = AuthService()
    
    token_response = auth.create_session_token(
        google_id="123456789",
        email="user@example.com"
    )
    
    assert 'access_token' in token_response
    assert token_response['token_type'] == 'bearer'
    assert token_response['expires_in'] == 86400  # 24 hours

def test_verify_session_token():
    """Test session token verification"""
    auth = AuthService()
    
    # Create token
    token_response = auth.create_session_token(
        google_id="123456789",
        email="user@example.com"
    )
    
    # Verify token
    payload = auth.verify_session_token(token_response['access_token'])
    
    assert payload['sub'] == "123456789"
    assert payload['email'] == "user@example.com"

def test_invalid_token():
    """Test invalid token rejection"""
    auth = AuthService()
    
    with pytest.raises(ValueError):
        auth.verify_session_token("invalid.token.here")
```

### Manual Testing

```powershell
# 1. Start backend
cd backend
python -m uvicorn app.main:app --reload

# 2. Test health endpoint
Invoke-WebRequest http://localhost:8000/health

# 3. Get Google token (from browser console after login)
# Then test auth endpoint:
$token = "google_id_token_here"
$body = @{token=$token} | ConvertTo-Json

Invoke-WebRequest -Uri "http://localhost:8000/auth/google" `
    -Method POST `
    -Headers @{"Content-Type"="application/json"} `
    -Body $body

# 4. Test protected endpoint with session token
$sessionToken = "returned_access_token"

Invoke-WebRequest -Uri "http://localhost:8000/auth/me" `
    -Headers @{"Authorization"="Bearer $sessionToken"}
```

---

## Security Considerations

### ✅ Do's

- ✅ Verify Google token signature
- ✅ Check token expiration
- ✅ Store session tokens securely (hashed in database)
- ✅ Use HTTPS in production
- ✅ Set HTTPOnly cookies for session tokens
- ✅ Implement CSRF protection
- ✅ Log authentication events
- ✅ Rate limit auth endpoints

### ❌ Don'ts

- ❌ Don't log or expose session tokens
- ❌ Don't transmit tokens in URL parameters
- ❌ Don't trust client timestamps
- ❌ Don't allow infinite session duration
- ❌ Don't mix production and development secrets
- ❌ Don't expose detailed error messages to users
- ❌ Don't store user passwords (OAuth handles this)

### CSRF Protection

Add to FastAPI app:

```python
from fastapi_csrf_protect import CsrfProtect
from pydantic import BaseModel

@CsrfProtect.load_config
def get_csrf_config():
    return CsrfSettings(secret_key=os.getenv("SESSION_SECRET"))

app = FastAPI()
CsrfProtect(app)
```

---

## Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| "Invalid token" | Google token expired | Get fresh token from Google |
| "Wrong issuer" | Token from wrong source | Ensure correct OAuth flow |
| "Token not verified" | Missing/wrong client ID | Check GOOGLE_CLIENT_ID in .env |
| "User not found" | Session invalid | User logged out or deleted |
| "401 Unauthorized" | No Authorization header | Include: `Authorization: Bearer <token>` |

---

## Next Steps After Phase 2

Phase 2 provides the foundation for:
- **Phase 3:** User-specific data ingestion tracking
- **Phase 6:** User personalization in briefings
- **Phase 7:** User conversation history in chat
- **Phase 8:** User analytics and insights
- **Phase 9:** User profile in frontend

---

## Resources

- [Google OAuth 2.0 Documentation](https://developers.google.com/identity/protocols/oauth2)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [JWT Best Practices](https://tools.ietf.org/html/rfc8949)
- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)

---

*Phase 2 Skills Guide*  
*Created: January 31, 2026*  
*Status: Foundation Complete*

