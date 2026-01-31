import { useState, useEffect } from 'react'
import { auth, signInWithGoogle, signOutUser } from './firebase'
import Chat from './components/Chat'
import './App.css'

function App() {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const unsubscribe = auth.onAuthStateChanged((user) => {
      setUser(user)
      setLoading(false)
    })
    return () => unsubscribe()
  }, [])

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
          <button onClick={signInWithGoogle} className="btn-login">
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
