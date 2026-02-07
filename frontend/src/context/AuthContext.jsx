import { createContext, useContext, useState, useEffect } from 'react'
import { auth, signInWithGoogle, signOutUser, handleRedirectResult, sendPasswordlessEmail, completeEmailSignIn, isSignInWithEmailLink } from '../firebase'
import { onAuthStateChanged } from 'firebase/auth'

const AuthContext = createContext()

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return context
}

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [authError, setAuthError] = useState(null)

  useEffect(() => {
    const initialize = async () => {
      // Check if this is an email link sign-in
      if (isSignInWithEmailLink(auth, window.location.href)) {
        try {
          setLoading(true)
          const params = new URLSearchParams(window.location.search)
          const urlEmail = params.get('email')
          let savedEmail = null
          try {
            savedEmail = window.localStorage.getItem('emailForSignIn')
          } catch (e) {}
          
          const emailToUse = urlEmail || savedEmail
          
          if (emailToUse) {
            const user = await completeEmailSignIn(emailToUse)
            setUser(user)
            setLoading(false)
            return
          }
        } catch (error) {
          console.error('Email link sign-in error:', error)
          setAuthError(error.message)
          setLoading(false)
          return
        }
      }

      // Try to handle redirect result first
      try {
        const result = await handleRedirectResult()
        if (result) {
          setUser(result)
          setLoading(false)
          return
        }
      } catch (error) {
        console.error('Redirect result error:', error)
        setAuthError(error.message)
      }

      // Set up auth state listener
      const unsubscribe = onAuthStateChanged(auth, (user) => {
        setUser(user)
        setLoading(false)
      })

      return () => unsubscribe()
    }

    initialize()
  }, [])

  const handleSignInWithGoogle = async () => {
    try {
      setAuthError(null)
      await signInWithGoogle()
    } catch (error) {
      console.error('Google sign-in error:', error)
      setAuthError(error.message)
    }
  }

  const handleSignOut = async () => {
    try {
      await signOutUser()
      setUser(null)
    } catch (error) {
      console.error('Sign out error:', error)
      setAuthError(error.message)
    }
  }

  const handlePasswordlessEmail = async (email) => {
    try {
      setAuthError(null)
      await sendPasswordlessEmail(email)
      return true
    } catch (error) {
      console.error('Passwordless email error:', error)
      setAuthError(error.message)
      return false
    }
  }

  const value = {
    user,
    loading,
    authError,
    setAuthError,
    signInWithGoogle: handleSignInWithGoogle,
    signOut: handleSignOut,
    sendPasswordlessEmail: handlePasswordlessEmail
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
