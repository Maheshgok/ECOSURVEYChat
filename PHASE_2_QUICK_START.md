# Phase 2: Quick Start Guide

**Status:** Ready to Implement  
**Duration:** 2-3 hours  
**Goal:** Add Google OAuth authentication to the app

---

## Quick Reference

```powershell
# 1. Setup Google Cloud
# Go to console.cloud.google.com and create OAuth credentials

# 2. Update .env
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret

# 3. Install dependencies
cd backend
pip install google-auth-oauthlib==1.1.0 google-auth==2.25.2 python-jose[cryptography]==3.3.0 python-multipart==0.0.6

# 4. Create database migration
psql -U postgres -d survey_chat -f backend/migrations/002_add_auth_tables.sql

# 5. Run app
python -m uvicorn app.main:app --reload

# 6. Test
curl -X POST http://localhost:8000/auth/google -H "Content-Type: application/json" -d '{"token":"google_id_token"}'
```

---

## Step-by-Step Implementation

### Step 1: Google Cloud Setup (15 minutes)

#### 1.1 Create GCP Project

```
1. Go to https://console.cloud.google.com/
2. Click "Select a Project" → "New Project"
3. Name: "econsurvey-chat"
4. Click "Create"
5. Wait for project creation (2-3 minutes)
```

#### 1.2 Enable Google+ API

```
1. Click "APIs & Services" → "Enable APIs and Services"
2. Search for "Google+ API"
3. Click "Google+ API"
4. Click "Enable"
```

#### 1.3 Create OAuth Credentials

```
1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "OAuth Client ID"
3. If prompted, configure OAuth consent screen first:
   - User Type: External
   - Add required scopes:
     - openid
     - email
     - profile
4. Application Type: Web Application
5. Name: "EcoSurvey Chat"
6. Authorized JavaScript Origins:
   - http://localhost:3000
   - http://localhost:8000
7. Authorized Redirect URIs:
   - http://localhost:8000/auth/google/callback
   - http://localhost:3000/auth/callback
8. Click "Create"
9. Copy Client ID and Client Secret
```

#### 1.4 Save to .env

```powershell
# Edit .env in project root
$env:GOOGLE_CLIENT_ID = "your-client-id.apps.googleusercontent.com"
$env:GOOGLE_CLIENT_SECRET = "your-client-secret"

# Add to .env file
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback
```

### Step 2: Create Database Migration (5 minutes)

Create `backend/migrations/002_add_auth_tables.sql`:

```sql
-- Phase 2: User and Session Tables
-- Required for Google OAuth authentication

-- Users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    google_id VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    picture VARCHAR(500),
    email_verified BOOLEAN DEFAULT FALSE,
    
    first_login TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_google_id ON users(google_id);
CREATE INDEX idx_users_email ON users(email);

-- Sessions table
CREATE TABLE sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    token VARCHAR(500) UNIQUE NOT NULL,
    
    ip_address VARCHAR(45),
    user_agent VARCHAR(500),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    is_active BOOLEAN DEFAULT TRUE
);

CREATE INDEX idx_sessions_token ON sessions(token);
CREATE INDEX idx_sessions_user_id ON sessions(user_id);

-- Add user_id to conversations for user-specific tracking
ALTER TABLE conversations ADD COLUMN user_id INTEGER REFERENCES users(id) ON DELETE SET NULL;

-- Add user_id to sessions (already done above, but keeping for clarity)
-- CREATE INDEX idx_conversations_user_id ON conversations(user_id);
```

### Step 3: Install Dependencies (5 minutes)

```powershell
cd backend

# Install new packages
pip install google-auth-oauthlib==1.1.0
pip install google-auth==2.25.2
pip install python-jose[cryptography]==3.3.0
pip install python-multipart==0.0.6

# Verify installation
pip list | findstr "google-auth|python-jose"
```

### Step 4: Create Auth Service (20 minutes)

Create `backend/app/services/auth_service.py` with OAuth token verification and session management.

See: [02_Phase2_OAuth_Skills.md](02_Phase2_OAuth_Skills.md#backend-implementation) for full implementation

### Step 5: Create Models (10 minutes)

Update `backend/app/models/__init__.py`:

Add `User` and `Session` models (see skills guide for full code)

### Step 6: Create Auth Routes (20 minutes)

Update `backend/app/api/auth.py`:

Implement:
- `POST /auth/google` - Login with Google token
- `POST /auth/logout` - Logout
- `GET /auth/me` - Get current user

### Step 7: Create Dependencies (10 minutes)

Create `backend/app/core/dependencies.py`:

Implements `get_current_user()` for protecting routes.

### Step 8: Update Main App (5 minutes)

Update `backend/app/main.py`:

```python
from app.api import auth

app.include_router(auth.router)  # Add this line
```

### Step 9: Run Database Migration (5 minutes)

```powershell
# Ensure PostgreSQL is running
psql -U postgres -d survey_chat -f backend/migrations/002_add_auth_tables.sql

# Verify tables created
psql -U postgres -d survey_chat -c "\dt users, sessions"
```

### Step 10: Test (10 minutes)

```powershell
# Start backend
cd backend
python -m uvicorn app.main:app --reload

# In another terminal, test endpoints:

# 1. Health check (should still work)
curl http://localhost:8000/health

# 2. Auth check (will fail without token, but app is ready)
curl http://localhost:8000/auth/me

# 3. Full test requires real Google token (see Testing section)
```

---

## Testing

### Test 1: Verify Installation

```powershell
cd backend

# Should complete without errors
python -c "
from app.services.auth_service import AuthService
from app.models import User, Session
print('✓ Imports successful')
"
```

### Test 2: Start Server

```powershell
cd backend
python -m uvicorn app.main:app --reload

# Expected output:
# INFO:     Application startup complete
# INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Test 3: Manual Authentication

```powershell
# This requires getting a real Google ID token
# For Phase 2 testing:

# 1. Install Google Auth library
npm install google-auth-library  # In frontend

# 2. Get token in browser console:
# gapi.auth2.getAuthInstance().currentUser.get().getAuthResponse().id_token

# 3. Test auth endpoint (replace TOKEN with real token):
$token = "YOUR_GOOGLE_ID_TOKEN"
$body = @{token=$token} | ConvertTo-Json

$response = Invoke-WebRequest `
  -Uri "http://localhost:8000/auth/google" `
  -Method POST `
  -Headers @{"Content-Type"="application/json"} `
  -Body $body

Write-Output $response.Content | ConvertFrom-Json
# Should return:
# {
#   "access_token": "...",
#   "token_type": "bearer",
#   "user": {...}
# }
```

### Test 4: Protected Endpoints

```powershell
# Using session token from auth response:
$sessionToken = "RETURNED_ACCESS_TOKEN"

# Get current user
$response = Invoke-WebRequest `
  -Uri "http://localhost:8000/auth/me" `
  -Headers @{"Authorization"="Bearer $sessionToken"}

Write-Output $response.Content
# Should return user info
```

### Test 5: Logout

```powershell
# Invalidate session
$response = Invoke-WebRequest `
  -Uri "http://localhost:8000/auth/logout" `
  -Method POST `
  -Headers @{"Authorization"="Bearer $sessionToken"}

# Subsequent calls with this token should fail
```

---

## Success Checklist

Use this to verify Phase 2 is complete:

- [ ] Google Cloud project created
- [ ] OAuth credentials obtained and stored in .env
- [ ] Dependencies installed: `pip list | findstr "google-auth"`
- [ ] Database migration applied: `psql -d survey_chat -c "\dt users"`
- [ ] AuthService created: `backend/app/services/auth_service.py`
- [ ] User and Session models added to models
- [ ] Auth routes implemented: `backend/app/api/auth.py`
- [ ] Dependencies helper created: `backend/app/core/dependencies.py`
- [ ] FastAPI includes auth router
- [ ] Server starts without errors: `python -m uvicorn app.main:app --reload`
- [ ] Health endpoint works: `curl http://localhost:8000/health`
- [ ] Auth endpoints respond: `curl http://localhost:8000/auth/me` (401 expected)

---

## Expected Outputs

### Server Startup
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
INFO:app.main: Starting Economic Survey Chat v1.2
```

### Auth Success Response
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "name": "User Name",
    "picture": "https://...",
    "first_login": "2026-01-31T..."
  }
}
```

### Auth Failure Response
```json
{
  "detail": "Invalid token"
}
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "ModuleNotFoundError: google" | Run `pip install google-auth-oauthlib` |
| "GOOGLE_CLIENT_ID not set" | Add to .env and reload terminal |
| "Connection refused" | Start PostgreSQL: `Start-Service -Name postgresql-x64-15` |
| "User not found" | Create database tables: `psql -f 002_add_auth_tables.sql` |
| "Invalid token" | Use fresh Google ID token, not access token |
| "401 Unauthorized" | Include `Authorization: Bearer <token>` header |

---

## Next Phase

After Phase 2 is validated:
- **Phase 3:** Data ingestion from files
- **Phase 4:** PDF extraction
- **Phase 5:** LLM-assisted data processing

---

## Files to Create/Modify

| File | Action | Lines |
|------|--------|-------|
| `.env` | Add OAuth credentials | 2 lines |
| `backend/migrations/002_add_auth_tables.sql` | Create | 60 lines |
| `backend/requirements.txt` | Add 4 packages | +4 lines |
| `backend/app/services/auth_service.py` | Create | ~150 lines |
| `backend/app/models/__init__.py` | Add User, Session models | +50 lines |
| `backend/app/api/auth.py` | Implement | ~200 lines |
| `backend/app/core/dependencies.py` | Create | ~60 lines |
| `backend/app/main.py` | Include auth router | +1 line |

**Total New Code:** ~530 lines  
**Total Time:** 2-3 hours

---

*Phase 2 Quick Start - January 31, 2026*

