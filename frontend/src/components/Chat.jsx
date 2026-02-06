import { useState, useRef, useEffect } from 'react'
import { getAuthToken } from '../firebase'
import ReactMarkdown from 'react-markdown'
import './Chat.css'

function Chat({ user }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const messagesEndRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(scrollToBottom, [messages])

  const sendMessage = async (e) => {
    e.preventDefault()
    if (!input.trim() || loading) return

    const userMessage = { role: 'user', content: input }
    setMessages(prev => [...prev, userMessage])
    const currentInput = input
    setInput('')
    setLoading(true)

    try {
      const token = await getAuthToken()
      if (!token) {
        throw new Error('Failed to get authentication token. Please try signing out and back in.')
      }
      
      console.log('Sending request to backend...', { 
        userId: user.uid, 
        messageCount: messages.length,
        hasToken: !!token 
      })
      
      // Use absolute path to API
      const apiUrl = '/chatbot/ecosurveybudget2026/api/rag-chat-v2'
      
      // Build conversation history from messages (exclude current user message)
      const conversationHistory = messages.map(msg => ({
        role: msg.role,
        content: msg.content
      }))

      const response = await fetch(apiUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          question: currentInput,
          session_id: `session-${user.uid}`,
          conversation_history: conversationHistory,
          top_k: 5
        })
      })
      
      console.log('Backend response status:', response.status)

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        console.error('Backend error:', response.status, errorData)
        throw new Error(errorData.detail || `Server error: ${response.status}`)
      }

      const data = await response.json()
      console.log('Backend response received:', { 
        hasCitations: data.citations?.length > 0, 
        contextUsed: data.context_used 
      })
      
      // Detect guardrail violation: no citations and no context used
      const isBlocked = data.citations?.length === 0 && data.context_used === 0
      
      const assistantMessage = {
        role: 'assistant',
        content: data.answer,
        citations: data.citations || [],
        isBlocked: isBlocked,
        turnNumber: data.turn_number
      }
      
      setMessages(prev => [...prev, assistantMessage])
    } catch (error) {
      console.error('Error sending message:', error)
      
      // Provide specific error messages with details for debugging
      let errorMessage = '❌ Sorry, there was an error processing your request.'
      
      if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError')) {
        errorMessage = '🌐 **Network Error**\n\nYour network may be blocking our API server. This is common on:\n• Corporate networks\n• School/university WiFi\n• Public WiFi with restrictions\n\n**Try:**\n1. Switch to mobile data/hotspot\n2. Try a different network\n3. Contact your IT department about accessing: ecosurvey-backend-812016027146.asia-south1.run.app'
      } else if (error.message.includes('401') || error.message.includes('Unauthorized')) {
        errorMessage = '🔒 **Authentication Error**\n\nYour login session may have expired or is blocked by browser settings.\n\n**Try:**\n1. Sign out and sign back in\n2. Clear browser cache\n3. Try incognito/private mode'
      } else if (error.message.includes('Failed to get authentication token')) {
        errorMessage = '🔒 **Authentication Token Error**\n\nCouldn\'t get your login credentials. This may happen if:\n• Browser storage is blocked\n• Session expired\n• Privacy settings are too strict\n\n**Try:**\n1. Sign out and sign back in\n2. Enable cookies/storage for this site\n3. Try a different browser'
      } else if (error.message.includes('404')) {
        errorMessage = '📭 No relevant information found for your question. Try rephrasing or asking something more general.'
      } else if (error.message.includes('500')) {
        errorMessage = '⚠️ Server error. Our team has been notified. Please try again in a moment.'
      } else if (error.message) {
        // Show actual error message for better debugging
        errorMessage = `❌ ${error.message}`
      }
      
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: errorMessage,
        error: true
      }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="chat-wrapper">
      {/* Left Drawer */}
      <div className={`drawer ${drawerOpen ? 'open' : ''}`}>
        <div className="drawer-content">
          <section className="drawer-section">
            <h4>Features</h4>
            <ul className="drawer-list">
              <li>📊 Evidence-grounded answers with citations</li>
              <li>� Conversational context across turns</li>
              <li>🔒 Multi-layer security guardrails</li>
              <li>🎯 Practitioner-grade economic insights</li>
              <li>📈 Real-time data from Economic Survey</li>
            </ul>
          </section>

          <section className="drawer-section">
            <h4>Sample Questions</h4>
            <button className="sample-question" onClick={() => { setInput("What are India's GDP growth projections for FY27?"); setDrawerOpen(false); }}>
              What are India's GDP growth projections for FY27?
            </button>
            <button className="sample-question" onClick={() => { setInput("Explain the inflation trends in the latest survey"); setDrawerOpen(false); }}>
              Explain the inflation trends in the latest survey
            </button>
            <button className="sample-question" onClick={() => { setInput("What does the survey say about employment data?"); setDrawerOpen(false); }}>
              What does the survey say about employment data?
            </button>
            <button className="sample-question" onClick={() => { setInput("Compare consumption patterns across sectors"); setDrawerOpen(false); }}>
              Compare consumption patterns across sectors
            </button>
          </section>

          <section className="drawer-section">
            <h4>Data Sources</h4>
            <ul className="drawer-list">
              <li>Economic Survey PDFs</li>
              <li>Statistical Tables</li>
              <li>Charts & Visualizations</li>
              <li>Index Reports</li>
              <li>Government Publications</li>
            </ul>
          </section>
        </div>
      </div>

      {/* Drawer Overlay */}
      {drawerOpen && <div className="drawer-overlay" onClick={() => setDrawerOpen(false)} />}

      {/* Main Chat Area */}
      <div className="chat-container">
        <button className="drawer-toggle" onClick={() => setDrawerOpen(!drawerOpen)}>
          {drawerOpen ? '→' : '←'}
        </button>

        <div className="messages">
        {messages.map((msg, idx) => (
          <div key={idx} className={`message ${msg.role} ${msg.isBlocked ? 'blocked' : ''}`}>
            <div className="message-avatar">
              {msg.role === 'user' ? (
                <img src={user.photoURL} alt="You" />
              ) : (
                <div className={`bot-avatar ${msg.isBlocked ? 'blocked' : ''}`}>
                  {msg.isBlocked ? '🛡️' : '🤖'}
                </div>
              )}
            </div>
            <div className="message-content">
              {msg.role === 'user' ? (
                <p>{msg.content}</p>
              ) : (
                <>
                  {msg.isBlocked && (
                    <div className="blocked-banner">
                      <span className="blocked-icon">⚠️</span>
                      <span className="blocked-text">Request Blocked by Security</span>
                    </div>
                  )}
                  <ReactMarkdown>{msg.content}</ReactMarkdown>
                  {msg.citations && msg.citations.length > 0 && (
                    <div className="citations">
                      <h4>📚 Sources</h4>
                      <div className="citations-list">
                        {msg.citations.map((citation, i) => (
                          <div key={i} className="citation-item">
                            <div className="citation-source">
                              <strong>{citation.document}</strong>
                              {citation.chapter && <span className="citation-meta"> • {citation.chapter}</span>}
                              {citation.page && <span className="citation-meta"> • Page {citation.page}</span>}
                            </div>
                            <div className="citation-score">
                              Relevance: {(citation.score * 100).toFixed(0)}%
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        ))}
        
        {loading && (
          <div className="message assistant">
            <div className="message-avatar">
              <div className="bot-avatar">🤖</div>
            </div>
            <div className="message-content">
              <div className="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      <form onSubmit={sendMessage} className="input-form">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a question about the survey data..."
          disabled={loading}
        />
        <button type="submit" disabled={loading || !input.trim()}>
          {loading ? '⏳' : '📤'}
        </button>
      </form>
      </div>
    </div>
  )
}

export default Chat
