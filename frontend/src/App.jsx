import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import Navigation from './components/Navigation'
import Homepage from './components/Homepage'
import ChatStandard from './pages/ChatStandard'
import ChatGraphRAG from './pages/ChatGraphRAG'
import ProtectedRoute from './components/ProtectedRoute'
import './App.css'

function App() {
  return (
    <Router>
      <AuthProvider>
        <div className="app">
          <Navigation />
          <Routes>
            <Route path="/" element={<Homepage />} />
            <Route 
              path="/chat" 
              element={
                <ProtectedRoute>
                  <ChatStandard />
                </ProtectedRoute>
              } 
            />
            <Route 
              path="/graphrag" 
              element={
                <ProtectedRoute>
                  <ChatGraphRAG />
                </ProtectedRoute>
              } 
            />
          </Routes>
        </div>
      </AuthProvider>
    </Router>
  )
}

export default App
