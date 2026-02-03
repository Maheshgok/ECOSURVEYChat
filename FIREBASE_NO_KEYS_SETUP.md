# 🔐 Firebase Setup WITHOUT Service Account Keys

## ✅ Good News: You Don't Need Service Account Keys!

Your organization's policy is actually **protecting you from a security risk**. Service account keys are dangerous if leaked. Here are **better alternatives**:

---

## 🎯 What Works Without Keys

### 1. Frontend (Already Perfect) ✅
**No keys needed!** Frontend uses public Firebase config:

```javascript
// frontend/src/firebase.js
const firebaseConfig = {
  apiKey: "AIza...",              // ✅ Public value, safe to expose
  authDomain: "your-app.firebaseapp.com",
  projectId: "your-project-id",
  storageBucket: "your-app.appspot.com",
  messagingSenderId: "123456789",
  appId: "1:123456789:web:abc123"
}
```

**Get these from:**
```
Firebase Console → Project Settings → General → Your apps → Web app
```

### 2. Backend Token Verification (Already Perfect) ✅
**No keys needed!** Our `firebase_auth.py` already uses **public key verification**:

```python
# backend/app/services/firebase_auth.py
# Uses Google's public certificates (no secrets needed)
GOOGLE_CERTS_URL = "https://www.googleapis.com/robot/v1/metadata/x509/..."
```

This is **more secure** than service account keys!

### 3. Firestore (Needs Solution)
This is the **only** part that needs credentials. Here are your options:

---

## 🚀 Solution Options (No Keys Required)

### Option A: Application Default Credentials (RECOMMENDED) ✅

**Best for**: Cloud Run, GCE, GKE  
**Security**: ✅ No keys to manage  
**Setup**: Automatic

#### How It Works
Cloud Run automatically provides credentials through the environment. No configuration needed!

#### Update Firestore Service
```python
# backend/app/services/firestore_sessions.py
# Change initialization to:

def _ensure_initialized(self):
    """Lazy initialization of Firebase Admin SDK"""
    if self._initialized:
        return
    
    try:
        if not firebase_admin._apps:
            # Try Application Default Credentials FIRST
            try:
                # This works on Cloud Run, GCE, GKE automatically
                firebase_admin.initialize_app()
                logger.info("Firebase Admin initialized with Application Default Credentials")
            except Exception as e:
                logger.warning(f"ADC not available: {e}")
                # Fallback: try other methods if needed
                if settings.FIREBASE_CREDENTIALS_JSON:
                    cred_dict = json.loads(settings.FIREBASE_CREDENTIALS_JSON)
                    cred = credentials.Certificate(cred_dict)
                    firebase_admin.initialize_app(cred)
                    logger.info("Firebase Admin initialized with inline credentials")
                else:
                    raise Exception("No credentials available for Firestore")
        
        self.db = firestore.client()
        self.sessions_collection = self.db.collection('chat_sessions')
        self._initialized = True
        logger.info("Firestore session service initialized")
    except Exception as e:
        logger.error(f"Failed to initialize Firestore: {e}")
        self._initialized = False
```

#### For Cloud Run (Production)
**Just set this one env var:**
```bash
FIREBASE_PROJECT_ID=your-project-id
```

Cloud Run automatically has access to Firestore! ✅

#### For Local Development
Use `gcloud auth application-default login`:

```bash
# One-time setup
gcloud auth application-default login

# This creates credentials at:
# Windows: %APPDATA%\gcloud\application_default_credentials.json
# Mac/Linux: ~/.config/gcloud/application_default_credentials.json
```

Then just set in `.env`:
```bash
FIREBASE_PROJECT_ID=your-project-id
```

---

### Option B: Workload Identity Federation (Advanced)

**Best for**: Multi-cloud or complex setups  
**Security**: ✅✅ Most secure  
**Setup**: Complex

Use short-lived tokens instead of static keys. See: https://cloud.google.com/iam/docs/workload-identity-federation

---

### Option C: Make Firestore Optional (Quick Win)

**Best for**: MVP, testing  
**Security**: ✅ No credentials needed  
**Setup**: Already done!

Sessions just won't persist across server restarts. Everything else works.

#### Already Implemented
Our Firestore service already has graceful fallback:

```python
# If Firestore fails to initialize:
self._initialized = False

# Then save_session returns False (doesn't crash)
# And get_session returns None (uses in-memory only)
```

**To disable Firestore temporarily:**
```bash
# In .env, just DON'T set FIREBASE_CREDENTIALS_PATH
# App works fine without it!
```

---

## 📝 Updated Setup Instructions

### Step 1: Update Firestore Service (REQUIRED)

Let me update the code to prioritize Application Default Credentials:

```python
# I'll update this in the next step
```

### Step 2: Local Development Setup

```bash
# 1. Authenticate with Google Cloud
gcloud auth application-default login

# 2. Set project
gcloud config set project your-firebase-project-id

# 3. Update .env (NO KEYS!)
FIREBASE_PROJECT_ID=your-firebase-project-id
# REMOVE: FIREBASE_CREDENTIALS_PATH
# REMOVE: FIREBASE_CREDENTIALS_JSON
```

### Step 3: Cloud Run Setup

```bash
# Deploy with just project ID
gcloud run services update ecosurvey-backend-v2 \
  --update-env-vars FIREBASE_PROJECT_ID=your-project-id \
  --region=asia-south1 \
  --project=watch-mail-trial

# Cloud Run automatically has Firestore access! ✅
```

### Step 4: Grant Cloud Run Service Account Access (If Needed)

```bash
# Find your Cloud Run service account
gcloud run services describe ecosurvey-backend-v2 \
  --region=asia-south1 \
  --format="value(spec.template.spec.serviceAccountName)"

# Grant Firestore access
gcloud projects add-iam-policy-binding your-project-id \
  --member="serviceAccount:SERVICE_ACCOUNT_EMAIL" \
  --role="roles/datastore.user"
```

---

## 🧪 Testing Without Keys

### Test Local Setup
```bash
# 1. Login
gcloud auth application-default login

# 2. Start backend
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

**Expected logs:**
```
INFO: Firebase Admin initialized with Application Default Credentials
INFO: Firestore session service initialized
```

### Test Cloud Run
```bash
# Deploy
cd backend
..\deploy_v2.ps1

# Test
curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  https://ecosurvey-backend-v2-...run.app/api/rag-chat-v2/health
```

---

## 🔒 Security Benefits

### With Service Account Keys (OLD) ❌
- Keys are long-lived (never expire)
- If leaked = permanent access
- Must rotate manually
- Stored in files (can be committed to Git)
- Single point of failure

### Without Keys (NEW) ✅
- Tokens are short-lived (1 hour)
- If leaked = limited window
- Auto-rotation
- No files to protect
- Built-in audit trail
- Follows principle of least privilege

---

## 🆘 Troubleshooting

### Error: "Could not automatically determine credentials"

**Local:**
```bash
gcloud auth application-default login
gcloud config set project your-project-id
```

**Cloud Run:**
```bash
# Check service account has Firestore access
gcloud projects get-iam-policy your-project-id \
  --flatten="bindings[].members" \
  --filter="bindings.role:datastore"
```

### Error: "Permission denied on Firestore"

```bash
# Grant datastore.user role to Cloud Run service account
gcloud projects add-iam-policy-binding your-project-id \
  --member="serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
  --role="roles/datastore.user"
```

### Firestore Disabled Entirely

```bash
# .env (no Firestore vars)
# Just omit FIREBASE_CREDENTIALS_PATH and FIREBASE_CREDENTIALS_JSON
# App works fine, sessions just don't persist
```

---

## 📚 Resources

- **Application Default Credentials**: https://cloud.google.com/docs/authentication/application-default-credentials
- **Cloud Run Authentication**: https://cloud.google.com/run/docs/authenticating/service-to-service
- **Firestore Security**: https://firebase.google.com/docs/firestore/security/get-started
- **Best Practices**: https://cloud.google.com/iam/docs/best-practices-service-accounts

---

## ✅ Recommended Approach

**For your situation (can't create keys due to policy):**

1. ✅ **Use Application Default Credentials** (already secure!)
2. ✅ **Local**: `gcloud auth application-default login`
3. ✅ **Cloud Run**: Automatic (no config needed)
4. ✅ **Update code** to try ADC first (I'll do this next)

This is actually **MORE SECURE** than using service account keys! 🎉

---

Want me to update the code to use Application Default Credentials as the primary method?
