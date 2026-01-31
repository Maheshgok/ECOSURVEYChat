import { initializeApp } from 'firebase/app'
import { getAuth, signInWithPopup, GoogleAuthProvider, signOut } from 'firebase/auth'

const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID
}

const app = initializeApp(firebaseConfig)
export const auth = getAuth(app)

const provider = new GoogleAuthProvider()

export const signInWithGoogle = async () => {
  try {
    const result = await signInWithPopup(auth, provider)
    // Get Firebase ID token
    const idToken = await result.user.getIdToken()
    
    // Send to backend for authentication
    const response = await fetch('/api/auth/firebase', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token: idToken })
    })
    
    const data = await response.json()
    // Store backend access token
    localStorage.setItem('accessToken', data.access_token)
    
    return result.user
  } catch (error) {
    console.error('Error signing in:', error)
    throw error
  }
}

export const signOutUser = async () => {
  try {
    await signOut(auth)
    localStorage.removeItem('accessToken')
  } catch (error) {
    console.error('Error signing out:', error)
  }
}

export const getAuthToken = async () => {
  const user = auth.currentUser
  if (user) {
    return await user.getIdToken()
  }
  return null
}
