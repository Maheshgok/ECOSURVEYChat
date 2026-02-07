import Chat from '../components/Chat'
import { useAuth } from '../context/AuthContext'
import './ChatPage.css'

function ChatStandard() {
  const { user } = useAuth()

  return (
    <div className="chat-page">
      <div className="chat-header">
        <h1>Standard Chat</h1>
        <p>Fast conversational AI for Economic Survey queries</p>
      </div>
      <Chat user={user} mode="standard" />
    </div>
  )
}

export default ChatStandard
