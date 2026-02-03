# Firebase Migration Plan - Complete Auth & Session Management

## 🎯 Goal
Move ALL user management, session management, and authentication/authorization to Firebase, removing database dependencies and strengthening the core RAG functionality.

## ✅ Current State Analysis

### Already Implemented
- ✅ **Frontend**: Firebase Auth with Google OAuth
  - `firebase.js` configured with `signInWithGoogle()`, `signOutUser()`
  - Firebase ID tokens generated on login
  - User state management via `auth.onAuthStateChanged`

- ✅ **Backend**: Firebase token verification
  - `firebase_auth.py` service with public key verification
  - No service account needed (uses Google's public keys)
  - Token validation with JWT decode

- ✅ **Backend Endpoints**: Auth routes (DISABLED)
  - `auth.py` with `/auth/firebase` and `/auth/me`
  - Currently requires database (Supabase/PostgreSQL)
  - **Status**: Disabled in `main.py`

### Current Issues
- ❌ Backend auth depends on PostgreSQL database
- ❌ Session management not implemented (no conversation persistence)
- ❌ Frontend calls disabled `/api/auth/firebase` endpoint
- ❌ No authorization middleware for protected routes
- ❌ User data stored in PostgreSQL (coupling)

## 🚀 Migration Strategy

### Phase 1: Simplify Backend Auth (Remove Database)
**Goal**: Make backend stateless, verify Firebase tokens directly

**Changes**:
1. Remove database dependency from auth endpoints
2. Create lightweight auth middleware
3. Extract user info directly from Firebase token
4. No user table, no sessions table - Firebase handles it all

**Benefits**:
- Stateless backend (easier to scale)
- No database migrations
- Simpler code
- Firebase manages user lifecycle

### Phase 2: Add Firestore for Session Management
**Goal**: Persist conversation sessions in Firestore

**Why Firestore**:
- Integrated with Firebase Auth
- Real-time sync (optional)
- Generous free tier (50K reads/day, 20K writes/day)
- No server management
- Perfect for session data

**What to Store**:
- Session ID → User ID mapping
- Conversation history (last N messages)
- Session metadata (created_at, last_active)
- User preferences (optional)

### Phase 3: Update Frontend (Remove Backend Auth Call)
**Goal**: Use Firebase token directly for API calls

**Changes**:
1. Remove `/api/auth/firebase` call from `firebase.js`
2. Pass Firebase ID token in Authorization header
3. Backend validates token on each request (cached public keys)
4. No need for separate backend access token

### Phase 4: Add Authorization Middleware
**Goal**: Protect RAG endpoints with Firebase auth

**Implementation**:
- Middleware extracts Firebase token from header
- Validates token using `firebase_service`
- Adds user context to request
- Rate limiting per user (optional)

## 📋 Detailed Implementation Plan

### Step 1: Install Firestore SDK in Backend
```bash
pip install firebase-admin
```

Add to `requirements.txt`:
```
firebase-admin==6.4.0  # For Firestore session storage
```

### Step 2: Create Simplified Auth Middleware
**File**: `backend/app/core/firebase_middleware.py` (NEW)

```python
\"\"\"
Firebase Authentication Middleware - Stateless
No database required, validates tokens using public keys
\"\"\"
from fastapi import Request, HTTPException, status
from typing import Optional
from app.services.firebase_auth import firebase_service
import logging

logger = logging.getLogger(__name__)

async def get_current_user(request: Request) -> dict:
    \"\"\"
    Extract and validate Firebase user from Authorization header
    Returns user dict: {uid, email, name, picture}
    \"\"\"
    auth_header = request.headers.get('Authorization')
    
    if not auth_header or not auth_header.startswith('Bearer '):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Missing or invalid authorization header'
        )
    
    token = auth_header.replace('Bearer ', '')
    
    user = await firebase_service.verify_token(token)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid or expired token'
        )
    
    logger.info(f"Authenticated user: {user['email']}")
    return user

async def get_current_user_optional(request: Request) -> Optional[dict]:
    \"\"\"
    Same as get_current_user but returns None if not authenticated
    Use for endpoints that work with/without auth
    \"\"\"
    try:
        return await get_current_user(request)
    except HTTPException:
        return None
```

### Step 3: Create Firestore Session Service
**File**: `backend/app/services/firestore_sessions.py` (NEW)

```python
\"\"\"
Firestore Session Management
Stores conversation history and session metadata
\"\"\"
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import firebase_admin
from firebase_admin import credentials, firestore
from app.core.settings import settings
import logging

logger = logging.getLogger(__name__)

class FirestoreSessionService:
    \"\"\"Manage chat sessions in Firestore\"\"\"
    
    def __init__(self):
        # Initialize Firebase Admin SDK (once)
        if not firebase_admin._apps:
            if settings.FIREBASE_CREDENTIALS_JSON:
                # Use inline JSON (for Cloud Run)
                import json
                cred_dict = json.loads(settings.FIREBASE_CREDENTIALS_JSON)
                cred = credentials.Certificate(cred_dict)
            elif settings.FIREBASE_CREDENTIALS_PATH:
                # Use service account file (for local)
                cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
            else:
                # Use default credentials (Cloud Run has implicit auth)
                cred = credentials.ApplicationDefault()
            
            firebase_admin.initialize_app(cred)
        
        self.db = firestore.client()
        self.sessions_collection = self.db.collection('chat_sessions')
    
    async def get_session(self, session_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        \"\"\"
        Get session data from Firestore
        Validates that session belongs to user
        \"\"\"
        try:
            doc_ref = self.sessions_collection.document(session_id)
            doc = doc_ref.get()
            
            if not doc.exists:
                logger.info(f\"Session {session_id} not found\")
                return None
            
            data = doc.to_dict()
            
            # Verify ownership
            if data.get('user_id') != user_id:
                logger.warning(f\"Session {session_id} does not belong to user {user_id}\")
                return None
            
            return data
        
        except Exception as e:
            logger.error(f\"Error fetching session: {e}\")
            return None
    
    async def save_session(
        self,
        session_id: str,
        user_id: str,
        conversation_history: List[Dict[str, str]],
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        \"\"\"
        Save or update session in Firestore
        \"\"\"
        try:
            doc_ref = self.sessions_collection.document(session_id)
            
            # Keep only last 10 messages (limit storage)
            trimmed_history = conversation_history[-10:]
            
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
            else:
                doc_ref.update(session_data)
            
            logger.info(f\"Session {session_id} saved for user {user_id}\")
            return True
        
        except Exception as e:
            logger.error(f\"Error saving session: {e}\")
            return False
    
    async def delete_session(self, session_id: str, user_id: str) -> bool:
        \"\"\"Delete session (with ownership check)\"\"\"
        try:
            doc_ref = self.sessions_collection.document(session_id)
            doc = doc_ref.get()
            
            if not doc.exists:
                return False
            
            data = doc.to_dict()
            if data.get('user_id') != user_id:
                logger.warning(f\"Cannot delete session {session_id} - not owned by {user_id}\")
                return False
            
            doc_ref.delete()
            logger.info(f\"Session {session_id} deleted\")
            return True
        
        except Exception as e:
            logger.error(f\"Error deleting session: {e}\")
            return False
    
    async def cleanup_old_sessions(self, days: int = 30) -> int:
        \"\"\"
        Cleanup sessions older than N days
        Run periodically via Cloud Scheduler
        \"\"\"
        try:
            cutoff = datetime.now() - timedelta(days=days)
            
            # Query old sessions
            old_sessions = self.sessions_collection.where(
                'last_active', '<', cutoff
            ).stream()
            
            count = 0
            for doc in old_sessions:
                doc.reference.delete()
                count += 1
            
            logger.info(f\"Cleaned up {count} old sessions\")
            return count
        
        except Exception as e:
            logger.error(f\"Error cleaning up sessions: {e}\")
            return 0
    
    async def get_user_sessions(
        self,
        user_id: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        \"\"\"Get all sessions for a user (for session history UI)\"\"\"
        try:
            sessions = self.sessions_collection.where(
                'user_id', '==', user_id
            ).order_by(
                'last_active', direction=firestore.Query.DESCENDING
            ).limit(limit).stream()
            
            result = []
            for doc in sessions:
                data = doc.to_dict()
                data['session_id'] = doc.id
                result.append(data)
            
            return result
        
        except Exception as e:
            logger.error(f\"Error fetching user sessions: {e}\")
            return []


# Global instance
firestore_sessions = FirestoreSessionService()
```

### Step 4: Update RAG Chat v2 to Use Firebase + Firestore
**File**: `backend/app/api/rag_chat_v2.py` (UPDATE)

Add auth middleware:
```python
from fastapi import Depends
from app.core.firebase_middleware import get_current_user
from app.services.firestore_sessions import firestore_sessions

@router.post(\"/rag-chat-v2\", response_model=ChatResponse)
async def rag_chat_v2_endpoint(
    request: ChatRequest,
    user: dict = Depends(get_current_user)  # ← Add Firebase auth
):
    \"\"\"
    Advanced RAG chat with Firebase authentication
    \"\"\"
    user_id = user['uid']
    
    # Load session from Firestore (if exists)
    session_data = await firestore_sessions.get_session(
        session_id=request.session_id,
        user_id=user_id
    )
    
    # Use stored conversation history
    if session_data:
        conversation_history = session_data.get('conversation_history', [])
    else:
        conversation_history = request.conversation_history or []
    
    # ... existing RAG logic ...
    
    # Save updated session to Firestore
    conversation_history.append({\"role\": \"user\", \"content\": request.question})
    conversation_history.append({\"role\": \"assistant\", \"content\": answer})
    
    await firestore_sessions.save_session(
        session_id=request.session_id,
        user_id=user_id,
        conversation_history=conversation_history
    )
    
    return ChatResponse(...)
```

### Step 5: Update Frontend to Use Firebase Token Directly
**File**: `frontend/src/firebase.js` (UPDATE)

```javascript
// REMOVE backend auth call
export const signInWithGoogle = async () => {
  try {
    const result = await signInWithPopup(auth, provider)
    
    // That's it! No backend call needed
    // Frontend will pass Firebase token to API calls
    
    return result.user
  } catch (error) {
    console.error('Error signing in:', error)
    throw error
  }
}

// Helper to get current Firebase token
export const getAuthToken = async () => {
  const user = auth.currentUser
  if (!user) throw new Error('Not authenticated')
  
  // Get fresh token (Firebase handles refresh)
  return await user.getIdToken(/* forceRefresh */ false)
}
```

**File**: `frontend/src/components/Chat.jsx` (UPDATE - already done!)

The current implementation already passes Firebase token:
```javascript
const token = await getAuthToken()
const response = await fetch('/api/rag-chat-v2', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`  // ← Firebase token
  },
  body: JSON.stringify({
    question: input,
    session_id: `session-${user.uid}`,
    top_k: 5
  })
})
```

✅ **Frontend is already ready!**

### Step 6: Remove Database Dependency
**File**: `backend/app/main.py` (UPDATE)

Remove database imports:
```python
# REMOVE:
# from app.core.database import get_db
# from app.models import User

# Keep only:
from app.api import health, rag_chat, rag_chat_v2
```

### Step 7: Add Optional Auth to RAG Chat v1 (Basic)
**File**: `backend/app/api/rag_chat.py` (UPDATE)

```python
from app.core.firebase_middleware import get_current_user_optional

@router.post(\"/rag-chat\", response_model=ChatResponse)
async def rag_chat_endpoint(
    request: ChatRequest,
    user: Optional[dict] = Depends(get_current_user_optional)  # Optional auth
):
    \"\"\"Basic RAG chat - auth optional for backward compatibility\"\"\"
    
    # Apply guardrails (same as before)
    # ... existing logic ...
    
    # If authenticated, log user activity
    if user:
        logger.info(f\"RAG chat from authenticated user: {user['email']}\")
    
    return ChatResponse(...)
```

## 📊 Architecture Comparison

### Before (Current - Database-Coupled)
```
Frontend → Firebase Auth → Backend /auth/firebase → PostgreSQL User Table
                                                    ↓
Frontend → API Call → Backend checks database → RAG → Response
                           ↓
                    Supabase Sessions Table
```

### After (Firebase-Native - Stateless)
```
Frontend → Firebase Auth → Get ID Token
                              ↓
Frontend → API Call + Token → Backend validates token → RAG → Response
                                     ↓                        ↓
                              Firestore Sessions ← Save conversation
```

**Benefits**:
- ✅ No database dependency
- ✅ Stateless backend (easier scaling)
- ✅ Firebase handles user lifecycle
- ✅ Automatic token refresh
- ✅ Built-in rate limiting (Firebase quotas)
- ✅ Real-time session sync (optional)

## 🔒 Security Improvements

### Current Security
- ❌ Custom JWT tokens (backend generates)
- ❌ Database stores sessions
- ❌ Manual token refresh logic
- ❌ No built-in rate limiting

### Firebase Security
- ✅ Google-signed JWT tokens (industry standard)
- ✅ Automatic token refresh (Firebase SDK)
- ✅ Firestore security rules (server-side validation)
- ✅ Built-in rate limiting (Firebase quotas)
- ✅ DDoS protection (Firebase infrastructure)

### Firestore Security Rules
```javascript
// firestore.rules
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Chat sessions: users can only access their own
    match /chat_sessions/{sessionId} {
      allow read, write: if request.auth != null 
                        && request.auth.uid == resource.data.user_id;
      allow create: if request.auth != null 
                   && request.auth.uid == request.resource.data.user_id;
    }
  }
}
```

## 💰 Cost Analysis

### Current (PostgreSQL/Supabase)
- Supabase Free Tier: 500 MB database, 2 GB bandwidth
- Database queries: ~10 queries per chat request
- Session storage: ~1 KB per session
- **Estimated**: $0-25/month (depending on usage)

### Firebase (Auth + Firestore)
- **Firebase Auth**: FREE for unlimited users
- **Firestore Free Tier**:
  - 50K reads/day
  - 20K writes/day
  - 1 GB storage
- **Typical Usage**:
  - 1 read + 1 write per chat (session load/save)
  - 10K chats/day = 10K reads + 10K writes = FREE
- **Estimated**: $0/month (within free tier)

**Savings**: ~$25/month + simplified architecture

## 🚀 Migration Steps (Order of Execution)

### Step 1: Setup Firebase Admin SDK
```bash
cd backend
pip install firebase-admin
pip freeze > requirements.txt
```

### Step 2: Get Firebase Service Account
```bash
# Firebase Console → Project Settings → Service Accounts → Generate New Private Key
# Download JSON file
# Save as backend/firebase-service-account.json
# Add to .gitignore!
```

### Step 3: Update .env
```bash
# Add to .env
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_CREDENTIALS_PATH=backend/firebase-service-account.json
```

### Step 4: Create New Files
- `backend/app/core/firebase_middleware.py`
- `backend/app/services/firestore_sessions.py`

### Step 5: Update Existing Files
- `backend/app/api/rag_chat_v2.py` - Add auth + Firestore
- `backend/app/api/rag_chat.py` - Add optional auth
- `backend/app/main.py` - Remove database imports
- `frontend/src/firebase.js` - Simplify (remove backend auth call)

### Step 6: Test Locally
```bash
# Backend
cd backend
python -m uvicorn app.main:app --reload --port 8000

# Frontend  
cd frontend
npm run dev
```

### Step 7: Deploy
```bash
# Backend v2
cd backend
.\deploy_v2.ps1

# Frontend (Netlify auto-deploys on git push)
git add .
git commit -m \"feat: Migrate to Firebase auth + Firestore sessions\"
git push origin main
```

## 📝 Testing Checklist

After migration:

### Auth Testing
- [ ] Sign in with Google works
- [ ] Firebase token passed to backend
- [ ] Backend validates token correctly
- [ ] Unauthorized requests return 401
- [ ] Token expiry handled gracefully

### Session Testing
- [ ] Sessions created in Firestore
- [ ] Conversation history persisted
- [ ] Multi-turn conversations work
- [ ] User can only access their sessions
- [ ] Old sessions cleaned up (manual test)

### Backward Compatibility
- [ ] v1 endpoint still works (optional auth)
- [ ] v2 endpoint requires auth
- [ ] Guardrails still work
- [ ] Citations still display

## 🎯 Benefits Summary

### For You (Developer)
- ✅ **Simpler Code**: No database migrations, no user tables
- ✅ **Easier Scaling**: Stateless backend, Firebase handles load
- ✅ **Less Maintenance**: Firebase manages users, tokens, sessions
- ✅ **Better Security**: Industry-standard auth, automatic updates
- ✅ **Faster Development**: Focus on RAG, not auth boilerplate

### For Users
- ✅ **Reliable Auth**: Google-backed infrastructure
- ✅ **Faster Login**: No backend database roundtrip
- ✅ **Session Persistence**: Conversations saved automatically
- ✅ **Better Privacy**: Firestore security rules enforce isolation

### For Production
- ✅ **Cost Reduction**: Potentially $25/month savings
- ✅ **Better Performance**: Fewer database queries
- ✅ **Higher Reliability**: Firebase 99.95% SLA
- ✅ **Global CDN**: Firebase Auth is geo-distributed

## 🔄 Rollback Plan

If something goes wrong:

### Quick Rollback
1. Revert git commits: `git revert HEAD~3..HEAD`
2. Redeploy backend: `.\deploy_v2.ps1`
3. Database still exists (no data lost)

### Gradual Rollback
1. Keep both auth systems running
2. Feature flag: `USE_FIREBASE_AUTH=false`
3. Slowly migrate users
4. Monitor metrics

## 🎓 Recommendation

**YES - Proceed with Firebase migration!**

**Why**:
1. ✅ You already have 70% implemented (Firebase Auth service, frontend)
2. ✅ Firestore is perfect for session management (better than PostgreSQL)
3. ✅ Removes unnecessary complexity (no database, no migrations)
4. ✅ Cost savings (~$25/month)
5. ✅ Aligns with your goal: "remove focus from these tasks and strengthen the core"

**Migration Effort**: ~4-6 hours
**Risk**: LOW (can rollback easily)
**Impact**: HIGH (simpler architecture, better scalability)

## 📚 Next Steps

Want me to:
1. ✅ **Implement the migration** (create all files, update code)
2. ✅ **Test locally** (verify auth + sessions work)
3. ✅ **Deploy to production** (gradual rollout)
4. ✅ **Create monitoring** (Firestore usage, auth metrics)

Ready to proceed? 🚀
