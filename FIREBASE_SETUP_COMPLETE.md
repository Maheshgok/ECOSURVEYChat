# 🚀 Firebase Migration Complete - Setup Guide

## ✅ Migration Status: IMPLEMENTED

All code changes have been completed! Here's what was done and how to set it up.

## 🎯 What Changed

### Backend Changes
1. ✅ **Created Firebase Middleware** (`backend/app/core/firebase_middleware.py`)
   - Stateless authentication using Firebase ID tokens
   - No database dependency
   - Functions: `get_current_user()`, `get_current_user_optional()`

2. ✅ **Created Firestore Session Service** (`backend/app/services/firestore_sessions.py`)
   - Stores conversation history in Firestore
   - Replaces PostgreSQL session table
   - Methods: `get_session()`, `save_session()`, `delete_session()`, `cleanup_old_sessions()`

3. ✅ **Updated RAG Chat v2** (`backend/app/api/rag_chat_v2.py`)
   - **REQUIRES** Firebase authentication
   - Automatically loads/saves sessions to Firestore
   - Session history persisted across conversations

4. ✅ **Updated RAG Chat v1** (`backend/app/api/rag_chat.py`)
   - **OPTIONAL** Firebase authentication
   - Works with or without auth
   - Backward compatible

### Frontend Changes
5. ✅ **Simplified Firebase Auth** (`frontend/src/firebase.js`)
   - Removed backend `/api/auth/firebase` call
   - Firebase token passed directly to API
   - Cleaner, stateless design

6. ✅ **Updated Documentation** (`.env.example`)
   - Added Firebase configuration section
   - Removed deprecated Google OAuth section

## 🔧 Setup Instructions

### Step 1: Get Firebase Service Account (Local Development)

1. **Go to Firebase Console**
   - Visit: https://console.firebase.google.com/
   - Select your project

2. **Generate Service Account Key**
   ```
   Project Settings → Service Accounts → Generate New Private Key
   ```
   
3. **Save the JSON file**
   ```bash
   # Save as:
   backend/firebase-service-account.json
   
   # ⚠️ IMPORTANT: Add to .gitignore!
   echo "firebase-service-account.json" >> backend/.gitignore
   ```

### Step 2: Update .env File

Add these to your `.env` file:

```bash
# Firebase Configuration
FIREBASE_PROJECT_ID=your-actual-firebase-project-id

# For local development
FIREBASE_CREDENTIALS_PATH=backend/firebase-service-account.json

# Optional: For Cloud Run (leave commented for local)
# FIREBASE_CREDENTIALS_JSON={"type":"service_account",...}
```

**Find your FIREBASE_PROJECT_ID:**
- Firebase Console → Project Settings → General → Project ID

### Step 3: Enable Firestore (First Time Only)

1. **Firebase Console → Firestore Database → Create Database**
2. **Select Mode**: Start in **production mode**
3. **Select Location**: Choose closest to your users (e.g., `asia-south1`)
4. **Set Security Rules**:

```javascript
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

### Step 4: Install Dependencies (Already Done)

```bash
cd backend
pip install -r requirements.txt
# firebase-admin is already in requirements.txt ✅
```

### Step 5: Test Locally

#### Terminal 1: Start Backend
```powershell
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

**Expected Output:**
```
INFO:     Starting Economic Survey Practitioner Chat v1.2 (Pinecone-only mode)
INFO:     Firestore session service initialized
INFO:     App ready and running
INFO:     Uvicorn running on http://127.0.0.1:8000
```

#### Terminal 2: Start Frontend
```powershell
cd frontend
npm run dev
```

#### Test Authentication
1. **Open**: http://localhost:3000
2. **Sign in** with Google
3. **Ask a question**: "What are India's GDP growth projections?"
4. **Verify**:
   - Response received
   - Firebase token logged in backend
   - Session saved to Firestore

#### Check Firestore (Optional)
```
Firebase Console → Firestore Database → chat_sessions collection
```

You should see documents with structure:
```javascript
{
  user_id: "firebase-uid-here",
  conversation_history: [...],
  last_active: timestamp,
  message_count: 2,
  created_at: timestamp,
  metadata: {...}
}
```

## 🚀 Production Deployment

### Option 1: Use Application Default Credentials (Recommended)

Cloud Run has built-in Firebase access. No service account needed!

1. **Remove** these from Cloud Run environment variables:
   - `FIREBASE_CREDENTIALS_PATH` ❌
   - `FIREBASE_CREDENTIALS_JSON` ❌

2. **Keep** only:
   ```bash
   FIREBASE_PROJECT_ID=your-firebase-project-id
   ```

3. **Deploy**:
   ```powershell
   cd backend
   ..\deploy_v2.ps1
   ```

Cloud Run will automatically authenticate using its service account.

### Option 2: Inline JSON Credentials (Alternative)

If you want explicit credentials:

1. **Convert service account to single line**:
   ```powershell
   $json = Get-Content backend/firebase-service-account.json -Raw
   $compressed = $json -replace '\s+', ' '
   Write-Host $compressed
   ```

2. **Set in Cloud Run**:
   ```bash
   gcloud run services update ecosurvey-backend-v2 \
     --update-env-vars FIREBASE_CREDENTIALS_JSON='{"type":"service_account",...}' \
     --region=asia-south1 \
     --project=watch-mail-trial
   ```

## 🧪 Testing Guide

### Test 1: Authenticated Access (v2 - Required)
```powershell
# This will FAIL without authentication
$body = @{
    question = "What is GDP growth?"
    session_id = "test-session"
    top_k = 3
} | ConvertTo-Json

Invoke-RestMethod -Uri 'http://localhost:8000/api/rag-chat-v2' -Method POST -ContentType 'application/json' -Body $body
```

**Expected**: 401 Unauthorized ✅

```powershell
# With Firebase token (get from frontend after login)
$token = "your-firebase-token-here"

$response = Invoke-RestMethod `
  -Uri 'http://localhost:8000/api/rag-chat-v2' `
  -Method POST `
  -Headers @{"Authorization"="Bearer $token"} `
  -ContentType 'application/json' `
  -Body $body

Write-Host "Answer: $($response.answer)"
Write-Host "Session saved to Firestore!"
```

**Expected**: Answer + citations ✅

### Test 2: Optional Auth (v1 - Works Both Ways)
```powershell
# Without token - works!
$response = Invoke-RestMethod `
  -Uri 'http://localhost:8000/api/rag-chat' `
  -Method POST `
  -ContentType 'application/json' `
  -Body $body

Write-Host "Anonymous access works: $($response.citations.Count) citations"
```

**Expected**: Works without authentication ✅

### Test 3: Session Persistence
```powershell
# First message
$token = "your-firebase-token"
$body1 = @{
    question = "What are India's GDP projections?"
    session_id = "persist-test-001"
    top_k = 3
} | ConvertTo-Json

$response1 = Invoke-RestMethod `
  -Uri 'http://localhost:8000/api/rag-chat-v2' `
  -Method POST `
  -Headers @{"Authorization"="Bearer $token"} `
  -ContentType 'application/json' `
  -Body $body1

# Second message (follow-up)
$body2 = @{
    question = "Tell me more about inflation"
    session_id = "persist-test-001"  # Same session
    top_k = 3
} | ConvertTo-Json

$response2 = Invoke-RestMethod `
  -Uri 'http://localhost:8000/api/rag-chat-v2' `
  -Method POST `
  -Headers @{"Authorization"="Bearer $token"} `
  -ContentType 'application/json' `
  -Body $body2

Write-Host "Turn 1: $($response1.turn_number)"
Write-Host "Turn 2: $($response2.turn_number)"
```

**Expected**: Turn numbers increment (1, 2, 3...) ✅

## 🔍 Troubleshooting

### Issue: "Failed to initialize Firestore"

**Cause**: Service account not configured  
**Fix**:
1. Check `.env` has `FIREBASE_PROJECT_ID` and `FIREBASE_CREDENTIALS_PATH`
2. Verify JSON file exists at specified path
3. Check JSON file is valid (open in text editor)

### Issue: "Invalid or expired token"

**Cause**: Frontend not sending Firebase token  
**Fix**:
1. Verify user is signed in (check `auth.currentUser`)
2. Check `Authorization: Bearer <token>` header in request
3. Try force refresh: `user.getIdToken(true)`

### Issue: "Session not found"

**Cause**: Firestore not saving (initialization failed)  
**Fix**:
1. Check backend logs: "Session X saved to Firestore"
2. Verify Firestore security rules allow writes
3. Check Firebase Console → Firestore for session documents

### Issue: 401 Unauthorized on v1 endpoint

**Cause**: Sending token to v1 (optional auth)  
**Fix**: This is fine! v1 logs it but doesn't require it. Check logs for "Authenticated user" or "Anonymous user"

## 📊 Monitoring

### Check Firestore Usage
```
Firebase Console → Usage and Billing → Firestore
```

**Free Tier Limits:**
- 50,000 reads/day
- 20,000 writes/day
- 1 GB storage

**Typical Usage (10K chats/day):**
- 10K reads (session load)
- 10K writes (session save)
- Storage: ~100 MB

✅ Well within free tier!

### Check Backend Logs
```powershell
# Local
# Check terminal output for:
# - "Authenticated user: user@example.com"
# - "Session X saved to Firestore"
# - "Loaded N messages from Firestore"

# Production (Cloud Run)
gcloud logging read "resource.type=cloud_run_revision AND 
  resource.labels.service_name=ecosurvey-backend-v2 AND 
  (textPayload=~'Authenticated user' OR textPayload=~'Session.*saved')" \
  --limit=20 --project=watch-mail-trial
```

## 🎉 Success Criteria

After setup, verify:

- [ ] Backend starts without errors
- [ ] "Firestore session service initialized" in logs
- [ ] Frontend login works
- [ ] Questions return answers with citations
- [ ] Sessions appear in Firestore console
- [ ] Multi-turn conversations maintain context
- [ ] Backend logs show "Authenticated user: email"
- [ ] v1 endpoint works without auth
- [ ] v2 endpoint requires auth (401 without token)

## 🔄 Rollback Plan

If something breaks:

### Quick Rollback
```powershell
# Revert backend code
git checkout HEAD~1 backend/app/api/rag_chat_v2.py
git checkout HEAD~1 backend/app/api/rag_chat.py

# Remove new files
Remove-Item backend/app/core/firebase_middleware.py
Remove-Item backend/app/services/firestore_sessions.py

# Redeploy
cd backend
..\deploy_v2.ps1
```

### Gradual Rollback
- Frontend already backwards compatible (sends token, backend validates)
- Can disable Firestore by removing `FIREBASE_CREDENTIALS_PATH` from `.env`
- Sessions will just not persist (in-memory only)

## 📚 Documentation

- **Migration Plan**: [FIREBASE_MIGRATION_PLAN.md](./FIREBASE_MIGRATION_PLAN.md)
- **This Guide**: [FIREBASE_SETUP_COMPLETE.md](./FIREBASE_SETUP_COMPLETE.md)
- **API Docs**: http://localhost:8000/docs (after starting backend)

## 🆘 Need Help?

1. Check logs: Backend terminal or Cloud Logging
2. Verify Firebase config: `.env` file settings
3. Test Firestore: Check Firebase Console
4. Review security rules: Firestore → Rules tab

## 🚀 Ready to Deploy?

Run these commands:

```powershell
# 1. Test locally first
cd backend
python -m uvicorn app.main:app --reload --port 8000
# Open another terminal
cd frontend
npm run dev
# Test at http://localhost:3000

# 2. Deploy backend
cd backend
..\deploy_v2.ps1

# 3. Deploy frontend (Netlify auto-deploys on git push)
git add .
git commit -m "feat: Migrate to Firebase auth + Firestore sessions"
git push origin main
```

**All done!** 🎉 Your app now uses Firebase for authentication and Firestore for session management!
