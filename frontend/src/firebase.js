import { initializeApp } from 'firebase/app'
import { getAuth, signInWithRedirect, getRedirectResult, GoogleAuthProvider, signOut } from 'firebase/auth'

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
// Force account selection every time to avoid stale auth states
provider.setCustomParameters({
  prompt: 'select_account'
})

export const signInWithGoogle = async () => {
  try {
    // Use signInWithRedirect instead of popup - works on corporate/mobile devices
    // User will be redirected to Google, then back to the app
    await signInWithRedirect(auth, provider)
    // Note: This function won't return - page redirects to Google
  } catch (error) {
    console.error('Error initiating sign in:', error)
    throw error
  }
}

// Call this on app load to complete redirect-based sign in
export const handleRedirectResult = async () => {
  try {
    const result = await getRedirectResult(auth)
    if (result) {
      console.log('Sign in successful:', result.user.email)
      return result.user
    }
    return null
  } catch (error) {
    console.error('Error handling redirect:', error)
    // Provide user-friendly error messages
    if (error.code === 'auth/popup-blocked') {
      throw new Error('Popup blocked. Please allow popups for this site.')
    } else if (error.code === 'auth/web-storage-unsupported') {
      throw new Error('Browser storage disabled. Please enable cookies and try again.')
    } else if (error.code === 'auth/cancelled-popup-request') {
      throw new Error('Sign in cancelled. Please try again.')
    }
    throw error
  }
}

export const signOutUser = async () => {
  try {
    await signOut(auth)
  } catch (error) {
    console.error('Error signing out:', error)
  }
}

export const getAuthToken = async () => {
  const user = auth.currentUser
  if (!user) {
    throw new Error('Not authenticated')
  }
  
  // Get fresh token (Firebase handles refresh automatically)
  return await user.getIdToken(/* forceRefresh */ false)
}
