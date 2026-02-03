# 🚀 Quick Start WITHOUT Service Account Keys

## Problem Solved! ✅

Your organization blocks service account key creation? **That's actually MORE SECURE!** We've updated the code to work without any keys.

---

## 🎯 3-Minute Setup

### Step 1: Setup Local Development (30 seconds)

```powershell
# Login with your Google account
gcloud auth application-default login

# Set your Firebase project
gcloud config set project watch-mail-trial
```

**That's it!** No keys, no files, no secrets. ✅

---

### Step 2: Update .env (15 seconds)

```bash
# backend/.env
FIREBASE_PROJECT_ID=watch-mail-trial

# ❌ DON'T SET THESE (not needed!):
# FIREBASE_CREDENTIALS_PATH=...
# FIREBASE_CREDENTIALS_JSON=...
```

---

### Step 3: Test Backend (30 seconds)

```powershell
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

**Expected logs:**
```
INFO: Attempting Application Default Credentials (ADC)...
INFO: ✅ Firebase Admin initialized with Application Default Credentials (NO KEYS!)
INFO: 🔥 Firestore session service initialized successfully (using ADC)
```

---

### Step 4: Enable Firestore (1 minute)

1. Open: https://console.firebase.google.com/project/watch-mail-trial/firestore
2. Click "Create Database"
3. Choose **Production mode**
4. Location: **asia-south1** (closest to your users)
5. Click "Enable"

---

### Step 5: Set Security Rules (30 seconds)

In Firestore Console → Rules tab:

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Users can only read/write their own sessions
    match /chat_sessions/{sessionId} {
      allow read, write: if request.auth != null && 
                           request.auth.uid == resource.data.user_id;
      allow create: if request.auth != null && 
                       request.auth.uid == request.resource.data.user_id;
    }
  }
}
```

Click **Publish**.

---

### Step 6: Test Complete Flow (30 seconds)

```powershell
# Terminal 1: Backend
cd backend
python -m uvicorn app.main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend
npm run dev
```

Open http://localhost:3000 and test:
1. ✅ Sign in with Google
2. ✅ Ask a question
3. ✅ See answer with citations
4. ✅ Check Firestore Console → chat_sessions collection (should see your session!)

---

## ☁️ Deploy to Production (2 minutes)

### Cloud Run Deployment

```powershell
cd backend

# Deploy with ONLY project ID (no keys needed!)
gcloud run deploy ecosurvey-backend-v2 `
  --source . `
  --region=asia-south1 `
  --platform=managed `
  --allow-unauthenticated `
  --set-env-vars FIREBASE_PROJECT_ID=watch-mail-trial `
  --project=watch-mail-trial
```

**Cloud Run automatically has Firestore access!** ✅

---

## 🔒 Security Benefits

### Old Way (Service Account Keys) ❌
- Long-lived keys (never expire)
- If leaked = permanent damage
- Must store securely
- Manual rotation
- Can be committed to Git accidentally

### New Way (Application Default Credentials) ✅
- Short-lived tokens (auto-refresh every 1 hour)
- If leaked = limited 1-hour window
- Nothing to store
- Automatic rotation
- Cannot be committed to Git (doesn't exist!)
- **Google's recommended approach** 🎉

---

## 🧪 Testing

### Test Authentication
```powershell
# Get test token
$token = gcloud auth print-identity-token

# Test v2 endpoint (requires auth)
$headers = @{ Authorization = "Bearer $token" }
$body = @{ question = "What is India's GDP growth?" } | ConvertTo-Json
Invoke-RestMethod -Uri http://localhost:8000/api/rag-chat-v2 -Method POST -Headers $headers -Body $body -ContentType 'application/json'
```

### Check Firestore
1. Open: https://console.firebase.google.com/project/watch-mail-trial/firestore
2. Navigate to `chat_sessions` collection
3. Should see documents with your session IDs ✅

---

## 🆘 Troubleshooting

### "Could not automatically determine credentials"

**Solution:**
```powershell
gcloud auth application-default login
gcloud config set project watch-mail-trial
```

### "Permission denied: Missing or insufficient permissions"

**Solution:** Grant your service account Firestore access:
```powershell
# Find service account
gcloud run services describe ecosurvey-backend-v2 --region=asia-south1 --format="value(spec.template.spec.serviceAccountName)"

# Grant access (replace SERVICE_ACCOUNT_EMAIL)
gcloud projects add-iam-policy-binding watch-mail-trial `
  --member="serviceAccount:SERVICE_ACCOUNT_EMAIL" `
  --role="roles/datastore.user"
```

### Backend logs show "Firestore not initialized"

**Check:**
1. Did you run `gcloud auth application-default login`?
2. Is `FIREBASE_PROJECT_ID` set in .env?
3. Is Firestore enabled in Firebase Console?

### Sessions not persisting

**Check Firestore Console:**
- Navigate to `chat_sessions` collection
- If empty → check backend logs for errors
- If exists → check user_id matches Firebase Auth UID

---

## 📊 How It Works

### Local Development
```
1. You: gcloud auth application-default login
2. gcloud: Creates ~/.config/gcloud/application_default_credentials.json
3. Backend: Reads ADC file automatically
4. Firebase: Validates your identity
5. Firestore: Grants access based on your Google account
```

### Cloud Run Production
```
1. Cloud Run: Assigns service account to your container
2. Container: Automatically gets short-lived token
3. Firebase Admin SDK: Uses token automatically
4. Firestore: Validates service account has datastore.user role
5. Token: Auto-refreshes every hour
```

---

## ✅ Verification Checklist

After setup, verify these:

- [ ] Backend starts with "✅ Firebase Admin initialized with Application Default Credentials"
- [ ] Backend shows "🔥 Firestore session service initialized successfully (using ADC)"
- [ ] Frontend login works (Google OAuth)
- [ ] Questions return answers with citations
- [ ] Firestore Console shows `chat_sessions` collection with your sessions
- [ ] Multi-turn conversations maintain context
- [ ] Cloud Run deployment succeeds without errors
- [ ] Production endpoint works with Firebase Auth tokens

---

## 🎉 You're Done!

**No service account keys needed!**  
**No security risks!**  
**Google's recommended approach!**  

Your code now uses the most secure authentication method available. 🔐

---

## 📚 Learn More

- **Application Default Credentials**: https://cloud.google.com/docs/authentication/application-default-credentials
- **Firebase Admin SDK Auth**: https://firebase.google.com/docs/admin/setup#initialize_the_sdk_in_non-google_environments
- **Firestore Security Rules**: https://firebase.google.com/docs/firestore/security/get-started
- **Cloud Run Service Identity**: https://cloud.google.com/run/docs/securing/service-identity

---

Need help? Check [FIREBASE_NO_KEYS_SETUP.md](./FIREBASE_NO_KEYS_SETUP.md) for detailed explanation.
