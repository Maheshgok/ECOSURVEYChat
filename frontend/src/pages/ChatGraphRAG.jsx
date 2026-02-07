import { useState, useRef, useEffect } from 'react'
import { useAuth } from '../context/AuthContext'
import { getAuthToken } from '../firebase'
import ReactMarkdown from 'react-markdown'
import './ChatPage.css'

function ChatGraphRAG() {
  const { user } = useAuth()
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
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
        throw new Error('Failed to get authentication token')
      }

      // GraphRAG endpoint
      const apiUrl = '/api/graphrag/query'
      
      const response = await fetch(apiUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          question: currentInput,
          top_k: 10,
          use_graph_traversal: true
        })
      })

      if (!response.ok) {
        throw new Error(`API error: ${response.status}`)
      }

      const data = await response.json()
      
      // Format response with reasoning
      let formattedResponse = data.answer + '\n\n'
      
      if (data.reasoning_steps && data.reasoning_steps.length > 0) {
        formattedResponse += '**Reasoning:**\n'
        data.reasoning_steps.forEach((step, idx) => {
          formattedResponse += `${idx + 1}. ${step}\n`
        })
        formattedResponse += '\n'
      }
      
      if (data.supporting_facts && data.supporting_facts.length > 0) {
        formattedResponse += '**Supporting Facts:**\n'
        data.supporting_facts.slice(0, 3).forEach((fact, idx) => {
          formattedResponse += `- ${fact.subject} ${fact.predicate} ${fact.value_quantity || ''} ${fact.value_unit || ''}`
          if (fact.certainty_score) {
            formattedResponse += ` (certainty: ${(fact.certainty_score * 100).toFixed(0)}%)`
          }
          formattedResponse += '\n'
        })
      }

      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: formattedResponse,
        confidence: data.confidence
      }])

    } catch (error) {
      console.error('GraphRAG query error:', error)
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `Error: ${error.message}. Please make sure the GraphRAG backend is deployed and the Pinecone index exists.`
      }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="chat-page">
      <div className="chat-header graphrag">
        <h1>🔍 GraphRAG Chat</h1>
        <p>Explainable AI with cited facts and reasoning chains</p>
      </div>
      
      <div className="chat-container">
        <div className="messages-container">
          {messages.length === 0 && (
            <div className="welcome-message">
              <h2>Welcome to GraphRAG Chat!</h2>
              <p>Ask questions about the Economic Survey and get answers with:</p>
              <ul>
                <li>✓ Explicit reasoning chains</li>
                <li>✓ Fact citations with certainty scores</li>
                <li>✓ Multi-hop graph traversal</li>
                <li>✓ Quantitative analysis support</li>
              </ul>
              <p className="hint">Try: "What is the fiscal deficit target for FY2025-26?"</p>
            </div>
          )}

          {messages.map((msg, idx) => (
            <div key={idx} className={`message ${msg.role}`}>
              <div className="message-content">
                <ReactMarkdown>{msg.content}</ReactMarkdown>
                {msg.confidence && (
                  <div className="confidence-score">
                    Confidence: {(msg.confidence * 100).toFixed(0)}%
                  </div>
                )}
              </div>
            </div>
          ))}

          {loading && (
            <div className="message assistant">
              <div className="message-content loading">
                <div className="typing-indicator">
                  <span></span><span></span><span></span>
                </div>
                Analyzing facts and building reasoning chain...
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
            placeholder="Ask about the Economic Survey..."
            disabled={loading}
            className="message-input"
          />
          <button type="submit" disabled={loading || !input.trim()} className="send-button">
            {loading ? '...' : '→'}
          </button>
        </form>
      </div>
    </div>
  )
}

export default ChatGraphRAG
