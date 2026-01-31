# Netlify Deployment Guide

## Frontend Created! 🎉

Modern React + Vite frontend with:
- ✅ Firebase Google Authentication
- ✅ Real-time chat interface
- ✅ Markdown rendering for AI responses
- ✅ Evidence display from retrieved documents
- ✅ Responsive design

## Deploy to Netlify

### Step 1: Push Frontend to GitHub

```bash
cd "c:\Users\Dell 5330\OneDrive\Documents\ECOSURVEYCHat"
git add .
git commit -m "Add React frontend with Firebase auth"
git push
```

### Step 2: Connect to Netlify

1. Go to https://app.netlify.com/
2. Click **"Add new site"** → **"Import an existing project"**
3. Choose **GitHub** and authorize
4. Select your repository: `Maheshgok/ECOSURVEYChat`

### Step 3: Configure Build Settings

Netlify will auto-detect settings from `netlify.toml`, but verify:
- **Base directory**: `frontend`
- **Build command**: `npm run build`
- **Publish directory**: `frontend/dist`

### Step 4: Add Environment Variables

In Netlify dashboard, go to **Site settings** → **Environment variables**:

```
VITE_API_URL=https://your-backend-url.com
VITE_FIREBASE_API_KEY=your-firebase-api-key
VITE_FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
VITE_FIREBASE_PROJECT_ID=your-project-id
```

### Step 5: Update Firebase Config

Edit `frontend/src/firebase.js` with your Firebase project details:
```javascript
const firebaseConfig = {
  apiKey: process.env.VITE_FIREBASE_API_KEY,
  authDomain: process.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: process.env.VITE_FIREBASE_PROJECT_ID,
  // ... etc
}
```

### Step 6: Update Backend URL

In `netlify.toml`, update the API proxy:
```toml
[[redirects]]
  from = "/api/*"
  to = "https://YOUR-BACKEND-URL.com/api/:splat"
```

### Step 7: Deploy!

Click **"Deploy site"** - Should take 2-3 minutes

## Testing Locally

```bash
cd frontend
npm run dev
```

Visit http://localhost:3000

## Features

- **Google Sign-In**: Click "Sign in with Google"
- **Chat Interface**: Ask questions about survey data
- **Sample Questions**: Click suggested questions to start
- **Evidence Display**: See sources for AI responses
- **Markdown Support**: Rich formatting in responses

## Next Steps

1. ✅ Push code to GitHub
2. ✅ Deploy to Netlify
3. ⏳ Configure Firebase credentials
4. ⏳ Point Netlify to your backend
5. ⏳ Test end-to-end!
