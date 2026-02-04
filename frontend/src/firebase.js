import { initializeApp } from 'firebase/app'
import { 
  getAuth, 
  signInWithRedirect, 
  getRedirectResult, 
  GoogleAuthProvider, 
  signOut,
  sendSignInLinkToEmail,
  isSignInWithEmailLink,
  signInWithEmailLink,
  setPersistence,
  inMemoryPersistence,
  browserLocalPersistence,
  browserSessionPersistence
} from 'firebase/auth'

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

// Storage fallback hierarchy: localStorage → sessionStorage → memory
export const initializeAuth = async () => {
  // Try localStorage first (persists across browser sessions)
  try {
    await setPersistence(auth, browserLocalPersistence)
    console.log('Using localStorage persistence')
    return 'local'
  } catch (error) {
    console.warn('localStorage unavailable, trying sessionStorage:', error.code)
  }
  
  // Try sessionStorage (persists during browser session, often works when cookies disabled)
  try {
    await setPersistence(auth, browserSessionPersistence)
    console.log('Using sessionStorage persistence')
    return 'session'
  } catch (error) {
    console.warn('sessionStorage unavailable, using in-memory:', error.code)
  }
  
  // Fall back to in-memory (lost on page refresh)
  try {
    await setPersistence(auth, inMemoryPersistence)
    console.log('Using in-memory persistence (auth will be lost on refresh)')
    return 'none'
  } catch (error) {
    console.error('All persistence methods failed:', error)
    return 'none'
  }
}

const provider = new GoogleAuthProvider()
// Force account selection every time to avoid stale auth states
provider.setCustomParameters({
  prompt: 'select_account'
})

// Method 1: Google OAuth with redirect (requires cookies for persistence)
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
      throw new Error('Browser storage disabled. Try using email sign-in instead.')
    } else if (error.code === 'auth/cancelled-popup-request') {
      throw new Error('Sign in cancelled. Please try again.')
    }
    throw error
  }
}

// Method 2: Passwordless Email Link (works WITHOUT cookies/storage!)
export const sendPasswordlessEmail = async (email) => {
  const actionCodeSettings = {
    // URL you want to redirect back to after sign-in
    url: window.location.origin + '/?email=' + email,
    handleCodeInApp: true,
  }

  try {
    await sendSignInLinkToEmail(auth, email, actionCodeSettings)
    // Save email locally only for convenience (not required for auth)
    try {
      window.localStorage.setItem('emailForSignIn', email)
    } catch (e) {
      // Storage unavailable, that's ok - user will need to re-enter email
      console.log('Storage unavailable for email caching')
    }
    return true
  } catch (error) {
    console.error('Error sending sign-in email:', error)
    throw error
  }
}

// Complete email link sign-in
export const completeEmailSignIn = async (emailFromUser) => {
  if (!isSignInWithEmailLink(auth, window.location.href)) {
    return null
  }

  let email = emailFromUser
  
  // Try to get email from storage if not provided
  if (!email) {
    try {
      email = window.localStorage.getItem('emailForSignIn')
    } catch (e) {
      // Storage unavailable
    }
  }

  // If still no email, try from URL parameter
  if (!email) {
    const params = new URLSearchParams(window.location.search)
    email = params.get('email')
  }

  if (!email) {
    throw new Error('Please enter your email address to complete sign-in.')
  }

  try {
    const result = await signInWithEmailLink(auth, email, window.location.href)
    // Clean up
    try {
      window.localStorage.removeItem('emailForSignIn')
    } catch (e) {
      // Ignore
    }
    // Clean URL
    window.history.replaceState({}, document.title, window.location.pathname)
    return result.user
  } catch (error) {
    console.error('Error completing email sign-in:', error)
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

// Check if any storage is available
export const checkStorageAvailable = async () => {
  try {
    // Test localStorage
    localStorage.setItem('test', '1')
    localStorage.removeItem('test')
    return true
  } catch (e1) {
    try {
      // Test sessionStorage
      sessionStorage.setItem('test', '1')
      sessionStorage.removeItem('test')
      return true
    } catch (e2) {
      // No storage available
      return false
    }
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
