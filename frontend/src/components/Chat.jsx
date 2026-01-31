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
    setInput('')
    setLoading(true)

    try {
      const token = await getAuthToken()
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          message: input,
          conversation_id: null
        })
      })

      if (!response.ok) {
        throw new Error('Failed to get response')
      }

      const data = await response.json()
      const assistantMessage = {
        role: 'assistant',
        content: data.response,
        evidence: data.evidence
      }
      
      setMessages(prev => [...prev, assistantMessage])
    } catch (error) {
      console.error('Error sending message:', error)
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: '❌ Sorry, there was an error processing your request.',
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
        <div className="drawer-header">
          <h3>ECO Survey</h3>
          <button className="drawer-close" onClick={() => setDrawerOpen(false)}>✕</button>
        </div>
        
        <div className="drawer-content">
          <section className="drawer-section">
            <h4>📊 Data Sources</h4>
            <ul className="drawer-list">
              <li>Economic Survey PDFs</li>
              <li>Statistical Tables</li>
              <li>Charts & Visualizations</li>
              <li>Index Reports</li>
              <li>Government Publications</li>
            </ul>
          </section>

          <section className="drawer-section">
            <h4>✨ Features</h4>
            <ul className="drawer-list">
              <li>AI-Powered Analysis</li>
              <li>Evidence-Based Answers</li>
              <li>Multi-Source Retrieval</li>
              <li>Contextual Insights</li>
              <li>Real-time Processing</li>
              <li>Conversation History</li>
            </ul>
          </section>

          <section className="drawer-section">
            <h4>ℹ️ About</h4>
            <p className="drawer-text">
              ECO Survey Chat uses advanced AI to analyze economic survey data 
              and provide evidence-based insights. All responses are backed by 
              official government publications and statistical reports.
            </p>
          </section>
        </div>
      </div>

      {/* Drawer Overlay */}
      {drawerOpen && <div className="drawer-overlay" onClick={() => setDrawerOpen(false)} />}

      {/* Main Chat Area */}
      <div className="chat-container">
        <div className="chat-header">
          <button className="drawer-toggle" onClick={() => setDrawerOpen(!drawerOpen)}>
            ☰
          </button>
          <h2>ECO Survey Chat</h2>
        </div>

        <div className="messages">
        {messages.length === 0 && (
          <div className="welcome-message">
            <h2>👋 Welcome to ECO Survey Chat!</h2>
            <p>Ask questions about the survey data and get AI-powered insights.</p>
            <div className="sample-questions">
              <h3>Try asking:</h3>
              <button onClick={() => setInput("What are the key economic indicators?")}>
                What are the key economic indicators?
              </button>
              <button onClick={() => setInput("Show me GDP growth trends")}>
                Show me GDP growth trends
              </button>
              <button onClick={() => setInput("Summarize employment data")}>
                Summarize employment data
              </button>
            </div>
          </div>
        )}
        
        {messages.map((msg, idx) => (
          <div key={idx} className={`message ${msg.role}`}>
            <div className="message-avatar">
              {msg.role === 'user' ? (
                <img src={user.photoURL} alt="You" />
              ) : (
                <div className="bot-avatar">🤖</div>
              )}
            </div>
            <div className="message-content">
              {msg.role === 'user' ? (
                <p>{msg.content}</p>
              ) : (
                <>
                  <ReactMarkdown>{msg.content}</ReactMarkdown>
                  {msg.evidence && msg.evidence.length > 0 && (
                    <div className="evidence">
                      <h4>📚 Evidence</h4>
                      {msg.evidence.map((ev, i) => (
                        <div key={i} className="evidence-item">
                          <strong>{ev.source}</strong>
                          <p>{ev.text.substring(0, 200)}...</p>
                        </div>
                      ))}
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
