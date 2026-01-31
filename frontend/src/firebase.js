import { initializeApp } from 'firebase/app'
import { getAuth, signInWithPopup, GoogleAuthProvider, signOut } from 'firebase/auth'

// TODO: Replace with your Firebase config
const firebaseConfig = {
  apiKey: "YOUR_API_KEY",
  authDomain: "YOUR_PROJECT.firebaseapp.com",
  projectId: "YOUR_PROJECT_ID",
  storageBucket: "YOUR_PROJECT.appspot.com",
  messagingSenderId: "YOUR_SENDER_ID",
  appId: "YOUR_APP_ID"
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
