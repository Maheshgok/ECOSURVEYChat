# Authentication Skills (Phase 2)

**Goal:** Secure Google OAuth login without storing PII

---

## 📋 Prerequisites

- Phase 1 (Database) completed
- Google Cloud Console project created
- OAuth 2.0 credentials obtained
- Understanding of OAuth2/OIDC flow

---

## 🎯 Tasks Breakdown

### **Task 2.1: Configure Google OAuth Credentials**

**In Google Cloud Console:**
1. Enable Google+ API
2. Create OAuth 2.0 Client ID (Web application)
3. Set Authorized JavaScript origins:
   - `http://localhost:8000` (development)
   - `https://your-api-domain.com` (production)
4. Set Authorized redirect URIs:
   - `http://localhost:8000/auth/callback`
   - `https://your-api-domain.com/auth/callback`
5. Note down `CLIENT_ID` and `CLIENT_SECRET`

---

### **Task 2.2: Install Dependencies**

Add to `backend/requirements.txt`:
```
authlib==1.2.1
itsdangerous==2.1.2
```

---

### **Task 2.3: Create Authentication Models**

**File: `models/user.py`**
```python
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from app.core.database import Base

class User(Base):
    """
    CRITICAL: Only stores pseudonymous identifier.
    NEVER store email, name, or tokens.
    """
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    user_pseudo_id = Column(String(64), unique=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login = Column(DateTime(timezone=True))
```

**Update `migrations/001_init.sql`** to add users table:
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    user_pseudo_id VARCHAR(64) UNIQUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_login TIMESTAMPTZ
);

CREATE INDEX idx_users_pseudo_id ON users(user_pseudo_id);
```

---

### **Task 2.4: Create Authentication Service**

**File: `services/auth_service.py`**
```python
import hashlib
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from authlib.integrations.starlette_client import OAuth
from authlib.jose import jwt
from app.core.config import settings
from app.models.user import User

# Initialize OAuth
oauth = OAuth()
oauth.register(
    name='google',
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid profile'},
)

def generate_pseudo_id(google_sub: str) -> str:
    """
    Generate pseudonymous user ID from Google sub.
    CRITICAL: This is the ONLY identifier we store.
    """
    combined = f"{google_sub}{settings.SERVER_SALT}"
    return hashlib.sha256(combined.encode()).hexdigest()

def get_or_create_user(db: Session, google_sub: str) -> User:
    """
    Get existing user or create new one.
    CRITICAL: Never stores email/name, only pseudo_id.
    """
    pseudo_id = generate_pseudo_id(google_sub)
    
    user = db.query(User).filter(User.user_pseudo_id == pseudo_id).first()
    if not user:
        user = User(user_pseudo_id=pseudo_id, last_login=datetime.utcnow())
        db.add(user)
    else:
        user.last_login = datetime.utcnow()
    
    db.commit()
    db.refresh(user)
    return user
```

---

### **Task 2.5: Create Session Management**

**File: `core/sessions.py`**
```python
from datetime import datetime, timedelta
from typing import Optional
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from app.core.config import settings

class SessionManager:
    def __init__(self):
        self.serializer = URLSafeTimedSerializer(settings.SESSION_SECRET)
        self.max_age = 7 * 24 * 60 * 60  # 7 days
    
    def create_session(self, user_pseudo_id: str) -> str:
        """Create signed session token"""
        return self.serializer.dumps({'user_pseudo_id': user_pseudo_id})
    
    def validate_session(self, token: str) -> Optional[str]:
        """Validate session token and return user_pseudo_id"""
        try:
            data = self.serializer.loads(token, max_age=self.max_age)
            return data.get('user_pseudo_id')
        except (BadSignature, SignatureExpired):
            return None

session_manager = SessionManager()
```

---

### **Task 2.6: Create Auth Endpoints**

**File: `api/auth.py`**
```python
from fastapi import APIRouter, Depends, HTTPException, Response, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.auth_service import oauth, get_or_create_user
from app.core.sessions import session_manager

router = APIRouter()

@router.get("/login")
async def login(request: Request):
    """Redirect to Google OAuth"""
    redirect_uri = request.url_for('auth_callback')
    return await oauth.google.authorize_redirect(request, redirect_uri)

@router.get("/callback")
async def auth_callback(
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    """
    Handle Google OAuth callback.
    CRITICAL: Extract only 'sub', never store email/name.
    """
    try:
        # Get token from Google
        token = await oauth.google.authorize_access_token(request)
        
        # Verify and extract claims
        user_info = token.get('userinfo')
        if not user_info or 'sub' not in user_info:
            raise HTTPException(status_code=400, detail="Invalid user info")
        
        google_sub = user_info['sub']
        
        # CRITICAL: Do NOT access or store email, name, picture
        # Only use 'sub' to generate pseudo_id
        user = get_or_create_user(db, google_sub)
        
        # Create session
        session_token = session_manager.create_session(user.user_pseudo_id)
        
        # Set secure cookie
        response = RedirectResponse(url="/chat")
        response.set_cookie(
            key="session",
            value=session_token,
            httponly=True,
            secure=True,  # HTTPS only in production
            samesite="lax",
            max_age=7 * 24 * 60 * 60  # 7 days
        )
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Authentication failed: {str(e)}")

@router.post("/logout")
async def logout(response: Response):
    """Clear session cookie"""
    response.delete_cookie(key="session")
    return {"message": "Logged out successfully"}

@router.get("/me")
async def get_current_user(request: Request, db: Session = Depends(get_db)):
    """Get current user (for debugging only)"""
    session_token = request.cookies.get("session")
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    user_pseudo_id = session_manager.validate_session(session_token)
    if not user_pseudo_id:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    
    return {"user_pseudo_id": user_pseudo_id}
```

---

### **Task 2.7: Create Auth Dependency**

**File: `core/dependencies.py`**
```python
from fastapi import Request, HTTPException, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.sessions import session_manager
from app.models.user import User

async def get_current_user_pseudo_id(request: Request) -> str:
    """
    Dependency to get current authenticated user's pseudo ID.
    Use this in protected endpoints.
    """
    session_token = request.cookies.get("session")
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    user_pseudo_id = session_manager.validate_session(session_token)
    if not user_pseudo_id:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    
    return user_pseudo_id

async def get_current_user(
    request: Request,
    db: Session = Depends(get_db)
) -> User:
    """Get current user object from database"""
    user_pseudo_id = await get_current_user_pseudo_id(request)
    
    user = db.query(User).filter(User.user_pseudo_id == user_pseudo_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user
```

---

### **Task 2.5: Deployment Cookie Modes**

**CRITICAL:** Cookie settings in Task 2.3 assume same-domain deployment. If you deploy frontend on Netlify and backend on Cloud Run, cookies may not persist reliably.

#### **Mode 1: Same-Domain (Recommended)**

**Setup:**
- Serve frontend from backend's `/static` folder, OR
- Use same apex domain (e.g., `app.example.com` for both frontend and backend via reverse proxy)

**Cookie settings:**
```python
response.set_cookie(
    key="session",
    value=session_token,
    httponly=True,
    secure=True,  # HTTPS only
    samesite="lax",  # Works for same-domain
    max_age=7 * 24 * 60 * 60
)
```

**Advantages:**
- Cookies work automatically
- No CORS complications
- SSE (Server-Sent Events) works naturally with cookies

---

#### **Mode 2: Cross-Domain (Netlify + Cloud Run)**

**Setup:**
- Frontend: `https://<app>.netlify.app`
- Backend: `https://<service>.run.app`

**Required changes:**

1. **Update cookie settings:**
```python
response.set_cookie(
    key="session",
    value=session_token,
    httponly=True,
    secure=True,  # MUST be True for cross-domain
    samesite="none",  # Changed from "lax" to "none"
    max_age=7 * 24 * 60 * 60
)
```

2. **Add CORS middleware in `main.py`:**
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://<your-app>.netlify.app"],  # Explicit origin
    allow_credentials=True,  # CRITICAL for cookies
    allow_methods=["*"],
    allow_headers=["*"],
)
```

3. **Frontend fetch requests must include credentials:**
```javascript
// In all API calls
fetch('https://<backend>.run.app/api/chat', {
    method: 'POST',
    credentials: 'include',  # CRITICAL for sending cookies
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
})
```

4. **SSE considerations:**
```javascript
// EventSource with cookies requires same-origin OR proper CORS
const eventSource = new EventSource(
    'https://<backend>.run.app/api/chat/stream/123',
    { withCredentials: true }  // May not work in all browsers for cross-domain
);
// Consider polling or WebSocket as alternative for cross-domain SSE
```

**Disadvantages:**
- More complex CORS configuration
- Safari may block third-party cookies by default
- SSE with credentials may not work reliably cross-domain
- Debugging cookie issues is harder

**Recommendation:** Use Mode 1 (same-domain) unless you have strong reasons for Mode 2.

---

### **Task 2.8: Update Main App**

**File: `main.py`** (add auth router):
```python
from app.api import health, auth

app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(auth.router, prefix="/auth", tags=["authentication"])
```

---

### **Task 2.9: Add Privacy Disclosure to Frontend**

**File: `frontend/login.html`** (create):
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login - Economic Survey Chat</title>
</head>
<body>
    <div class="login-container">
        <h1>Economic Survey Practitioner Chat</h1>
        
        <div class="privacy-notice">
            <p><strong>Privacy Notice:</strong></p>
            <p>Login is required only to track usage during the free access period. 
            We do not store your name, email, or personal profile data.</p>
        </div>
        
        <a href="/auth/login" class="google-login-btn">
            Sign in with Google
        </a>
    </div>
</body>
</html>
```

---

## ✅ Acceptance Criteria

### **Test 1: OAuth Flow**
1. Visit `http://localhost:8000/auth/login`
2. Should redirect to Google login
3. After login, redirects back to app
4. Session cookie set

### **Test 2: No PII Stored**
```sql
SELECT * FROM users;
-- Should show ONLY: id, user_pseudo_id, created_at, last_login
-- Should NOT show: email, name, picture, tokens
```

### **Test 3: Session Validation**
```bash
# With valid session cookie
curl -b "session=<token>" http://localhost:8000/api/me
# Expected: {"user_pseudo_id": "..."}

# Without session cookie
curl http://localhost:8000/api/me
# Expected: 401 Unauthorized
```

### **Test 4: Pseudo ID Consistency**
- Same Google user logging in twice should get same `user_pseudo_id`
- Different Google users should get different `user_pseudo_id`

---

## 🎯 Deliverables Checklist

- [ ] `users` table created with only pseudo_id
- [ ] Google OAuth configured in Cloud Console
- [ ] `auth_service.py` with pseudo ID generation
- [ ] `sessions.py` with secure session management
- [ ] `/auth/login`, `/auth/callback`, `/auth/logout` endpoints
- [ ] `get_current_user_pseudo_id` dependency
- [ ] Privacy disclosure on login page
- [ ] No email/name/tokens stored anywhere
- [ ] Session cookies are HttpOnly, Secure, SameSite=Lax
- [ ] All tests pass

---

## 🚨 STOP CONDITION

**Before marking Phase 2 complete, verify:**

```bash
# Check database schema
docker-compose exec postgres psql -U postgres -d survey_chat -c "\d users"
```

**Verification checklist:**
- [ ] ✅ No `email` column
- [ ] ✅ No `name` column
- [ ] ✅ No `picture` column
- [ ] ✅ No `access_token` column
- [ ] ✅ No `refresh_token` column
- [ ] ✅ Only `user_pseudo_id` present

**If ANY of these columns exist → STOP and delete them immediately.**

---

## 🔗 Next Phase

Once all deliverables are complete and stop condition verified, proceed to:
- **Phase 3: XLSX Ingestion Skills** (if data files ready)
- **Phase 5: PDF Ingestion Skills** (if PDF files ready)
