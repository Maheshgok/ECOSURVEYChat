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
          } else {
            setEmailInput('')
            setUseEmailAuth(true)
            setAuthError('Please enter your email address to complete sign-in.')
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

      // Auto-detect storage availability
      const detectStorage = () => {
        let cookiesWork = false
        let sessionStorageWork = false
        let localStorageWork = false
        
        // Test cookies
        try {
          document.cookie = 'storagetest=1; SameSite=Lax'
          cookiesWork = document.cookie.indexOf('storagetest') !== -1
          document.cookie = 'storagetest=1; expires=Thu, 01-Jan-1970 00:00:01 GMT'
        } catch (e) {
          cookiesWork = false
        }
        
        // Test sessionStorage
        try {
          sessionStorage.setItem('storagetest', '1')
          sessionStorageWork = sessionStorage.getItem('storagetest') === '1'
          sessionStorage.removeItem('storagetest')
        } catch (e) {
          sessionStorageWork = false
        }
        
        // Test localStorage
        try {
          localStorage.setItem('storagetest', '1')
          localStorageWork = localStorage.getItem('storagetest') === '1'
          localStorage.removeItem('storagetest')
        } catch (e) {
          localStorageWork = false
        }
        
        console.log('Storage detection:', { cookiesWork, sessionStorageWork, localStorageWork })
        
        return { cookiesWork, sessionStorageWork, localStorageWork }
      }

      const storage = detectStorage()
      setCookiesDisabled(!storage.cookiesWork)

      // If NO storage available, force email auth
      if (!storage.cookiesWork && !storage.sessionStorageWork && !storage.localStorageWork) {
        console.log('No storage available - switching to email auth')
        setUseEmailAuth(true)
        setAuthError('⚠️ Browser storage is disabled. Using passwordless email sign-in.')
        setLoading(false)
        return
      }

      // If only sessionStorage works (cookies disabled but storage available)
      if (!storage.cookiesWork && (storage.sessionStorageWork || storage.localStorageWork)) {
        console.log('Cookies disabled but storage available - Google auth may work')
        // Let them try Google first, but show email option prominently
      }

      // Handle Google redirect result
      try {
        const redirectUser = await handleRedirectResult()
        if (redirectUser) {
          console.log('Redirect sign-in completed')
          setUser(redirectUser)
          setLoading(false)
          return
        }
      } catch (error) {
        console.error('Redirect auth error:', error)
        
        // Prevent redirect loops - only auto-switch to email if it's an auth error
        if (error.code === 'auth/popup-closed-by-user' || 
            error.code === 'auth/cancelled-popup-request' ||
            error.code === 'auth/user-cancelled') {
          // User cancelled - just show the sign-in screen again
          setLoading(false)
          return
        }
        
        if (error.message.includes('storage') || 
            error.message.includes('web-storage-unsupported') ||
            error.code === 'auth/web-storage-unsupported') {
          // Storage issue - auto-switch to email auth
          console.log('Storage error detected - switching to email auth')
          setUseEmailAuth(true)
          setAuthError('⚠️ Google sign-in requires browser storage. Please use email sign-in.')
        } else {
          // Other errors - show error but don't auto-switch
          setAuthError(`Sign-in error: ${error.message}`)
        }
      }

      // Check current auth state
      const currentUser = auth.currentUser
      setUser(currentUser)
      setLoading(false)
    }

    initialize()

    // Listen for auth state changes
    const unsubscribe = auth.onAuthStateChanged((user) => {
      setUser(user)
      if (loading) setLoading(false)
    })
    return () => unsubscribe()
  }, [])

  const handleSignIn = async () => {
    try {
      setAuthError(null)
      setLoading(true)
      await signInWithGoogle()
      // Page will redirect to Google - no code after this runs
    } catch (error) {
      console.error('Sign in error:', error)
      setLoading(false)
      setAuthError(error.message || 'Sign-in failed. Please try email sign-in.')
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
            <div className="info-box" style={{ background: '#f0fdf4', borderColor: '#86efac' }}>
              <p style={{ color: '#166534', margin: 0 }}>✉️ <strong>We've sent a sign-in link to:</strong></p>
              <p style={{ color: '#166534', fontSize: '1.1em', fontWeight: 600, margin: '10px 0' }}>{email}</p>
              <p style={{ fontSize: '0.9em', marginTop: '10px', color: '#166534' }}>
                Please click the link in your email to sign in.
              </p>
              <p style={{ fontSize: '0.85em', marginTop: '8px', color: '#15803d' }}>
                💡 The link works on any device - even if opened elsewhere!
              </p>
              <p style={{ fontSize: '0.85em', marginTop: '8px', color: '#15803d', fontWeight: 500 }}>
                📬 Don't see it? Check your spam/junk folder.
              </p>
            </div>
            <button 
              onClick={() => { setEmailSent(false); setEmail(''); }}
              className="btn-secondary"
              style={{ marginTop: '15px' }}
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
          
          {useEmailAuth ? (
            <div className="auth-methods">
              <div className="info-box" style={{ marginBottom: '15px', background: '#eff6ff', borderColor: '#93c5fd' }}>
                <p style={{ color: '#1e40af', margin: 0, fontSize: '1em' }}>✉️ <strong>Sign in with email</strong></p>
                <p style={{ fontSize: '0.85em', marginTop: '8px', color: '#1e40af' }}>
                  We'll send you a secure sign-in link.
                </p>
              </div>
              <form onSubmit={handleEmailSignIn} className="email-form">
                <input
                  type="email"
                  placeholder="your.email@example.com"
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
              {authError && (
                <div className="auth-error" style={{ marginTop: '10px' }}>
                  <p>{authError}</p>
                </div>
              )}
              <button 
                onClick={() => { setUseEmailAuth(false); setAuthError(null); setEmail(''); }}
                className="btn-secondary"
                style={{ marginTop: '15px' }}
              >
                ← Back to Google Sign-In
              </button>
            </div>
          ) : (
            <div className="auth-methods">
              {authError && (
                <div className="auth-error" style={{ marginBottom: '15px' }}>
                  <p>{authError}</p>
                </div>
              )}
              <div className="info-box" style={{ marginBottom: '15px', background: '#f0fdf4', borderColor: '#86efac' }}>
                <p style={{ color: '#166534', margin: 0, fontSize: '0.9em', lineHeight: '1.5' }}>
                  <strong>Quick Sign-In:</strong> Click Google below for instant access.<br/>
                  <span style={{ fontSize: '0.85em' }}>If Google doesn't work, use the email option instead.</span>
                </p>
              </div>
              <button onClick={handleSignIn} className="btn-login" disabled={loading}>
                <img src="https://www.gstatic.com/firebasejs/ui/2.0.0/images/auth/google.svg" alt="Google" />
                {loading ? 'Signing in...' : 'Sign in with Google'}
              </button>
              <div className="divider">
                <span>or</span>
              </div>
              <button 
                onClick={() => { setUseEmailAuth(true); setAuthError(null); }}
                className="btn-email-switch"
              >
                📧 Sign in with Email
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
