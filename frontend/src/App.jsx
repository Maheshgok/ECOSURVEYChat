import { useState, useEffect } from 'react'
import { auth, signInWithGoogle, signOutUser, handleRedirectResult, sendPasswordlessEmail, completeEmailSignIn, isSignInWithEmailLink } from './firebase'
import Chat from './components/Chat'
import './App.css'

function App() {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [authError, setAuthError] = useState(null)
  const [cookiesDisabled, setCookiesDisabled] = useState(false)
  const [emailAuthMode, setEmailAuthMode] = useState(false)
  const [email, setEmail] = useState('')
  const [emailSent, setEmailSent] = useState(false)
  const [useEmailAuth, setUseEmailAuth] = useState(false)
  const [emailInput, setEmailInput] = useState('')

  useEffect(() => {
    // Check if this is an email link sign-in
    const checkEmailLink = async () => {
      if (isSignInWithEmailLink(auth, window.location.href)) {
        try {
          setLoading(true)
          // Check if email is in URL or storage
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
            return true
          } else {
            // Need user to enter email
            setEmailInput('')
            setUseEmailAuth(true)
            setAuthError('Please enter your email address to complete sign-in.')
            setLoading(false)
            return true
          }
        } catch (error) {
          console.error('Email link sign-in error:', error)
          setAuthError(error.message)
          setLoading(false)
          return true
        }
      }
      return false
    }

    // Check email link first
    checkEmailLink().then((wasEmailLink) => {
      if (wasEmailLink) return

      // Check if cookies are enabled
      const checkCookies = () => {
        try {
          document.cookie = 'cookietest=1; SameSite=Lax'
          const cookiesEnabled = document.cookie.indexOf('cookietest') !== -1
          document.cookie = 'cookietest=1; expires=Thu, 01-Jan-1970 00:00:01 GMT'
          return cookiesEnabled
        } catch (e) {
          return false
        }
      }

      const cookiesAvailable = checkCookies()
      setCookiesDisabled(!cookiesAvailable)

      if (!cookiesAvailable) {
        // Auto-switch to email auth for cookie-less environments
        setUseEmailAuth(true)
        setAuthError('Browser cookies disabled. Using passwordless email sign-in.')
        setLoading(false)
        return
      }

      // Handle redirect result (for Google sign-in)
      handleRedirectResult()
        .then((redirectUser) => {
          if (redirectUser) {
            console.log('Redirect sign-in completed')
            setUser(redirectUser)
            setLoading(false)
          } else {
            const currentUser = auth.currentUser
            setUser(currentUser)
            setLoading(false)
          }
        })
        .catch((error) => {
          console.error('Redirect auth error:', error)
          if (error.message.includes('storage')) {
            // Storage issue - suggest email auth
            setUseEmailAuth(true)
            setAuthError('Browser storage restricted. Please use email sign-in instead.')
          } else {
            setAuthError(error.message || 'Authentication failed. Please try again.')
          }
          setLoading(false)
        })

      // Listen for auth state changes
      const unsubscribe = auth.onAuthStateChanged((user) => {
        setUser(user)
        if (loading) setLoading(false)
      })
      return () => unsubscribe()
    })
  }, [])

  const handleSignIn = async () => {
    try {
      setAuthError(null)
      await signInWithGoogle()
      // Page will redirect to Google - no code after this runs
    } catch (error) {
      console.error('Sign in error:', error)
      if (error.message.includes('storage') || error.message.includes('cookie')) {
        setUseEmailAuth(true)
        setAuthError('Google sign-in requires cookies. Please use email sign-in instead.')
      } else {
        setAuthError(error.message || 'Failed to sign in. Please try again.')
      }
    }
  }

  const handleEmailSignIn = async (e) => {
    e.preventDefault()
    if (!email.trim()) {
      setAuthError('Please enter a valid email address.')
      return
    }

    try {
      setAuthError(null)
      setLoading(true)
      await sendPasswordlessEmail(email.trim())
      setEmailSent(true)
      setLoading(false)
    } catch (error) {
      console.error('Email sign-in error:', error)
      setAuthError(error.message || 'Failed to send sign-in email. Please try again.')
      setLoading(false)
    }
  }

  const handleCompleteEmailSignIn = async (e) => {
    e.preventDefault()
    if (!emailInput.trim()) {
      setAuthError('Please enter your email address.')
      return
    }

    try {
      setAuthError(null)
      setLoading(true)
      const user = await completeEmailSignIn(emailInput.trim())
      setUser(user)
      setLoading(false)
    } catch (error) {
      console.error('Complete email sign-in error:', error)
      setAuthError(error.message || 'Failed to complete sign-in. Please try again.')
      setLoading(false)
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
    // If completing email link sign-in and need email input
    if (isSignInWithEmailLink(auth, window.location.href) && !emailInput) {
      return (
        <div className="app login">
          <div className="login-container">
            <h1>Complete Sign In</h1>
            <p>Please enter your email to complete sign-in</p>
            <form onSubmit={handleCompleteEmailSignIn} className="email-form">
              <input
                type="email"
                placeholder="Enter your email"
                value={emailInput}
                onChange={(e) => setEmailInput(e.target.value)}
                className="email-input"
                required
              />
              <button type="submit" className="btn-email">
                Complete Sign In
              </button>
            </form>
            {authError && (
              <div className="auth-error">
                <p>❌ {authError}</p>
              </div>
            )}
          </div>
        </div>
      )
    }

    // Email sent confirmation
    if (emailSent) {
      return (
        <div className="app login">
          <div className="login-container">
            <h1>Check Your Email</h1>
            <p>✉️ We sent a sign-in link to <strong>{email}</strong></p>
            <div className="info-box">
              <p>Click the link in your email to sign in.</p>
              <p style={{ fontSize: '0.85em', marginTop: '10px', color: '#6b7280' }}>
                The link works on any device - even if cookies are disabled!
              </p>
            </div>
            <button 
              onClick={() => { setEmailSent(false); setEmail(''); }}
              className="btn-secondary"
            >
              Use Different Email
            </button>
          </div>
        </div>
      )
    }

    return (
      <div className="app login">
        <div className="login-container">
          <h1>ECO Survey Chat</h1>
          <p>AI-powered survey data analysis</p>
          
          {authError && (
            <div className="auth-error">
              <p>{cookiesDisabled ? '⚠️' : '❌'} {authError}</p>
            </div>
          )}

          {useEmailAuth ? (
            <div className="auth-methods">
              <form onSubmit={handleEmailSignIn} className="email-form">
                <input
                  type="email"
                  placeholder="Enter your email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="email-input"
                  required
                  autoFocus
                />
                <button type="submit" className="btn-email" disabled={loading}>
                  {loading ? 'Sending...' : 'Send Sign-In Link'}
                </button>
              </form>
              <div className="info-box">
                <p>✨ <strong>Works on ALL devices</strong></p>
                <p style={{ fontSize: '0.85em', marginTop: '5px' }}>
                  No cookies, storage, or popups needed. Perfect for corporate devices!
                </p>
              </div>
              {!cookiesDisabled && (
                <button 
                  onClick={() => setUseEmailAuth(false)}
                  className="btn-secondary"
                >
                  Or use Google Sign-In
                </button>
              )}
            </div>
          ) : (
            <div className="auth-methods">
              <button onClick={handleSignIn} className="btn-login">
                <img src="https://www.gstatic.com/firebasejs/ui/2.0.0/images/auth/google.svg" alt="Google" />
                Sign in with Google
              </button>
              <div className="divider">
                <span>or</span>
              </div>
              <button 
                onClick={() => setUseEmailAuth(true)}
                className="btn-email-switch"
              >
                📧 Sign in with Email (no cookies needed)
              </button>
            </div>
          )}
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
