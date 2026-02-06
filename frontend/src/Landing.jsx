import { useState, useEffect } from 'react'
import { auth, signInWithGoogle, signOutUser, handleRedirectResult, sendPasswordlessEmail, isSignInWithEmailLink, completeEmailSignIn } from './firebase'
import './App.css'

function Landing() {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [authError, setAuthError] = useState(null)
  const [email, setEmail] = useState('')
  const [emailSent, setEmailSent] = useState(false)
  const [useEmailAuth, setUseEmailAuth] = useState(false)

  useEffect(() => {
    let mounted = true

    const initialize = async () => {
      // Check if this is an email link sign-in
      if (isSignInWithEmailLink(auth, window.location.href)) {
        try {
          const params = new URLSearchParams(window.location.search)
          const urlEmail = params.get('email')
          const savedEmail = window.localStorage.getItem('emailForSignIn')
          const emailToUse = urlEmail || savedEmail
          
          if (emailToUse) {
            const user = await completeEmailSignIn(emailToUse)
            if (mounted) {
              setUser(user)
              setLoading(false)
            }
            return
          }
        } catch (error) {
          if (mounted) setAuthError(error.message)
        }
      }

      // Handle Google OAuth redirect - only once
      try {
        const redirectUser = await handleRedirectResult()
        if (redirectUser && mounted) {
          console.log('Google sign-in successful:', redirectUser.email)
          setUser(redirectUser)
          // Clean URL without reloading
          window.history.replaceState({}, document.title, window.location.pathname)
        }
      } catch (error) {
        console.error('Auth error:', error)
        if (mounted) setAuthError(error.message)
      }

      // Listen for auth state changes
      const unsubscribe = auth.onAuthStateChanged((user) => {
        if (mounted) {
          setUser(user)
          setLoading(false)
        }
      })

      if (mounted) setLoading(false)
      
      return () => {
        mounted = false
        unsubscribe()
      }
    }

    initialize()
  }, []) // Empty dependency array - run only once

  const handleGoogleSignIn = async () => {
    try {
      setAuthError(null)
      await signInWithGoogle()
    } catch (error) {
      setAuthError(error.message)
    }
  }

  const handleEmailSignIn = async (e) => {
    e.preventDefault()
    try {
      setAuthError(null)
      await sendPasswordlessEmail(email)
      setEmailSent(true)
    } catch (error) {
      setAuthError(error.message)
    }
  }

  const handleSignOut = async () => {
    await signOutUser()
    setUser(null)
  }

  if (loading) {
    return (
      <div className="app">
        <div className="container">
          <div className="loading">Loading...</div>
        </div>
      </div>
    )
  }

  return (
    <div className="app">
      <div className="container" style={{ maxWidth: '900px', margin: '0 auto', padding: '40px 20px' }}>
        
        <div style={{ 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'center',
          marginBottom: '40px',
          padding: '20px',
          background: '#f8f9fa',
          borderRadius: '8px'
        }}>
          <h1 style={{ fontSize: '1.8rem', margin: 0, color: '#2c3e50' }}>
            Economic Survey Chat
          </h1>
          
          {user ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
              <span style={{ color: '#666' }}>✓ {user.email}</span>
              <button onClick={handleSignOut} style={{ padding: '8px 20px', background: '#fff', border: '1px solid #ddd', borderRadius: '6px', cursor: 'pointer', fontSize: '0.9rem' }}>
                Sign Out
              </button>
            </div>
          ) : (
            <div style={{ display: 'flex', gap: '10px' }}>
              {!useEmailAuth ? (
                <>
                  <button onClick={handleGoogleSignIn} style={{ padding: '10px 20px', background: 'white', border: '2px solid #1976d2', color: '#1976d2', borderRadius: '6px', cursor: 'pointer', fontSize: '0.95rem', fontWeight: '500' }}>
                    Sign in with Google
                  </button>
                  <button onClick={() => setUseEmailAuth(true)} style={{ padding: '10px 20px', background: 'white', border: '1px solid #ddd', borderRadius: '6px', cursor: 'pointer', fontSize: '0.95rem' }}>
                    Email Link
                  </button>
                </>
              ) : (
                <button onClick={() => setUseEmailAuth(false)} style={{ padding: '10px 20px', background: 'white', border: '1px solid #ddd', borderRadius: '6px', cursor: 'pointer', fontSize: '0.95rem' }}>
                  ← Back
                </button>
              )}
            </div>
          )}
        </div>

        <div style={{ marginBottom: '40px' }}>
          <h2 style={{ fontSize: '2rem', marginBottom: '15px', color: '#1976d2' }}>
            Welcome to the Economic Survey Chatbot
          </h2>
          <p style={{ fontSize: '1.1rem', color: '#666', lineHeight: '1.8', marginBottom: '30px' }}>
            Get intelligent answers about Economic Survey data using advanced AI technology.
          </p>
        </div>

        <div style={{ background: user ? '#e8f5e9' : '#f8f9fa', padding: '40px', borderRadius: '12px', textAlign: 'center', border: user ? '2px solid #4caf50' : '2px solid #ddd', marginBottom: '40px' }}>
          <h3 style={{ fontSize: '1.5rem', marginBottom: '20px', color: user ? '#2e7d32' : '#666' }}>
            {user ? '✓ Ready to Chat' : 'Chatbot Access'}
          </h3>
          
          {user ? (
            <a href="/chatbot/ecosurveybudget2026/" style={{ display: 'inline-block', padding: '18px 50px', background: '#4caf50', color: 'white', textDecoration: 'none', borderRadius: '8px', fontSize: '1.3rem', fontWeight: 'bold', boxShadow: '0 4px 8px rgba(0,0,0,0.15)' }}>
              Launch Chatbot →
            </a>
          ) : (
            <>
              <button disabled style={{ padding: '18px 50px', background: '#e0e0e0', color: '#999', border: 'none', borderRadius: '8px', fontSize: '1.3rem', fontWeight: 'bold', cursor: 'not-allowed', marginBottom: '15px' }}>
                Launch Chatbot
              </button>
              <p style={{ color: '#d32f2f', fontSize: '1.05rem', fontWeight: '500', margin: 0 }}>
                🔒 Please log in to access the chatbot
              </p>
            </>
          )}
        </div>

        {!user && useEmailAuth && (
          <div style={{ background: 'white', padding: '30px', borderRadius: '8px', border: '1px solid #ddd', marginBottom: '30px' }}>
            {authError && <div style={{ background: '#f8d7da', color: '#721c24', padding: '15px', borderRadius: '4px', marginBottom: '20px' }}>{authError}</div>}
            {!emailSent ? (
              <form onSubmit={handleEmailSignIn}>
                <h3 style={{ marginBottom: '15px', color: '#333' }}>Sign in with Email</h3>
                <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Enter your email" required style={{ width: '100%', padding: '15px', border: '2px solid #ddd', borderRadius: '8px', fontSize: '1rem', marginBottom: '15px', boxSizing: 'border-box' }} />
                <button type="submit" style={{ width: '100%', padding: '15px', background: '#1976d2', color: 'white', border: 'none', borderRadius: '8px', cursor: 'pointer', fontSize: '1.1rem', fontWeight: 'bold' }}>
                  Send Sign-in Link
                </button>
              </form>
            ) : (
              <div style={{ background: '#e8f5e9', padding: '20px', borderRadius: '8px', textAlign: 'center' }}>
                <p style={{ fontSize: '1.1rem', marginBottom: '10px' }}>✉️ Check your email!</p>
                <p style={{ color: '#666' }}>We've sent a sign-in link to <strong>{email}</strong></p>
              </div>
            )}
          </div>
        )}

        <div style={{ fontSize: '0.95rem', color: '#666', lineHeight: '1.8', padding: '20px', background: '#fafafa', borderRadius: '8px' }}>
          <h3 style={{ marginBottom: '10px', color: '#333' }}>About this Application</h3>
          <p>This chatbot provides intelligent answers about Economic Survey data using advanced RAG technology powered by OpenAI and Pinecone vector search.</p>
        </div>
      </div>
    </div>
  )
}

export default Landing
