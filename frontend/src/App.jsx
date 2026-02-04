import { useState, useEffect } from 'react'
import { auth, signInWithGoogle, signOutUser, handleRedirectResult } from './firebase'
import Chat from './components/Chat'
import './App.css'

function App() {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [authError, setAuthError] = useState(null)

  useEffect(() => {
    // Handle redirect result first (for signInWithRedirect)
    handleRedirectResult()
      .then((redirectUser) => {
        if (redirectUser) {
          console.log('Redirect sign-in completed')
        }
      })
      .catch((error) => {
        console.error('Redirect auth error:', error)
        setAuthError(error.message || 'Authentication failed. Please try again.')
      })

    // Then listen for auth state changes
    const unsubscribe = auth.onAuthStateChanged((user) => {
      setUser(user)
      setLoading(false)
    })
    return () => unsubscribe()
  }, [])

  const handleSignIn = async () => {
    try {
      setAuthError(null)
      await signInWithGoogle()
      // Page will redirect to Google - no code after this runs
    } catch (error) {
      console.error('Sign in error:', error)
      setAuthError(error.message || 'Failed to sign in. Please try again.')
    }
  }

  if (loading) {
    return (
      <div className="app loading">
        <div className="spinner"></div>
        <p>Loading...</p>
      </div>
    )
  }

  if (!user) {
    return (
      <div className="app login">
        <div className="login-container">
          <h1>ECO Survey Chat</h1>
          <p>AI-powered survey data analysis</p>
          {authError && (
            <div className="auth-error">
              <p>❌ {authError}</p>
              <p style={{ fontSize: '0.9em', marginTop: '10px' }}>
                💡 If using iPhone or corporate device, please ensure cookies are enabled.
              </p>
            </div>
          )}
          <button onClick={handleSignIn} className="btn-login">
            <img src="https://www.gstatic.com/firebasejs/ui/2.0.0/images/auth/google.svg" alt="Google" />
            Sign in with Google
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>Chat with the Economic Survey of India</h1>
        <div className="user-info">
          <a href="https://www.linkedin.com/in/mahesh-gokhale-64b11512/" target="_blank" rel="noopener noreferrer" className="linkedin-link">
            LinkedIn
          </a>
          <img src={user.photoURL} alt={user.displayName} className="user-avatar" />
          <span>{user.displayName}</span>
          <button onClick={signOutUser} className="btn-logout">Sign Out</button>
        </div>
      </header>
      <main className="app-main">
        <Chat user={user} />
      </main>
    </div>
  )
}

export default App
