# Firebase Authentication Setup Guide

## Overview
The application now supports Firebase Authentication as the primary authentication method. This provides:
- Production-ready authentication
- No manual session management
- Automatic token refresh
- Built-in security

## Setup Steps

### 1. Create Firebase Project
1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Create a new project or use existing
3. Enable Authentication → Sign-in method → Google

### 2. Get Service Account Credentials
1. Go to Project Settings → Service Accounts
2. Click "Generate new private key"
3. Save the JSON file securely (never commit to git!)

### 3. Configure Backend

**Option A: Using Credentials File (Development)**
```bash
# Add to backend/.env
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_CREDENTIALS_PATH=/path/to/serviceAccountKey.json
```

**Option B: Using Inline JSON (Production/Serverless)**
```bash
# Add to backend/.env
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_CREDENTIALS_JSON='{"type":"service_account","project_id":"...","private_key":"..."}'
```

**Option C: Testing Mode (Skip Auth)**
```bash
# Add to backend/.env
SKIP_AUTH_FOR_TESTING=True
```

### 4. Frontend Integration

**Install Firebase SDK**
```bash
npm install firebase
```

**Initialize Firebase (frontend)**
```javascript
import { initializeApp } from 'firebase/app';
import { getAuth, signInWithPopup, GoogleAuthProvider } from 'firebase/auth';

const firebaseConfig = {
  apiKey: "your-api-key",
  authDomain: "your-project.firebaseapp.com",
  projectId: "your-project-id"
};

const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
```

**Login Flow**
```javascript
// 1. Sign in with Google
const provider = new GoogleAuthProvider();
const result = await signInWithPopup(auth, provider);

// 2. Get ID token
const idToken = await result.user.getIdToken();

// 3. Send to backend
const response = await fetch('/api/auth/firebase', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ token: idToken })
});

const data = await response.json();
// data.access_token is the Firebase token - use for all API calls
```

**Making Authenticated Requests**
```javascript
// Get fresh token
const token = await auth.currentUser.getIdToken();

// Use in API calls
const response = await fetch('/api/chat', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({ /* ... */ })
});
```

## API Endpoints

### POST /auth/firebase
Authenticate with Firebase ID token (recommended)

**Request:**
```json
{
  "token": "eyJhbGc..."
}
```

**Response:**
```json
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "name": "User Name",
    "picture": "https://..."
  }
}
```

### POST /auth/google (Legacy)
Old Google OAuth flow - still supported but Firebase preferred

### GET /auth/me
Get current user info

**Headers:**
```
Authorization: Bearer <firebase_token>
```

## Benefits of Firebase Auth

✅ **Automatic Token Refresh** - Firebase SDK handles it
✅ **Built-in Security** - Industry-standard JWT verification
✅ **No Session Management** - Stateless authentication
✅ **Email Verification** - Built into Firebase
✅ **Password Reset** - Handled by Firebase
✅ **Multi-provider** - Easy to add other auth methods
✅ **Scalable** - No database session queries

## Migration from Legacy Auth

The backend supports both Firebase and legacy session tokens:
1. Frontend sends Firebase token → Verified by Firebase
2. Fallback to legacy session token if Firebase fails
3. Gradually migrate users to Firebase
4. Eventually deprecate legacy auth

## Testing

**Test Mode (No Firebase Required)**
```bash
# backend/.env
SKIP_AUTH_FOR_TESTING=True
```

This uses a test user from the database for development.

## Security Notes

- Never commit Firebase credentials to git
- Use environment variables for all secrets
- Firebase tokens expire after 1 hour (auto-refreshed by SDK)
- Backend verifies every token on every request
- Users are auto-created on first Firebase login

## Troubleshooting

**"Firebase not configured"**
- Check FIREBASE_PROJECT_ID is set
- Check credentials file path or JSON is valid

**"Invalid Firebase token"**
- Token may be expired (get fresh token)
- Check Firebase project ID matches

**401 Unauthorized**
- Check Authorization header format: `Bearer <token>`
- Verify token is current (not expired)
- Check user exists in database
