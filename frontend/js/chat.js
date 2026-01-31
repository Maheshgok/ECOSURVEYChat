// Chat Page Logic

class ChatManager {
    constructor() {
        this.conversationId = null;
        this.messageTranscript = [];
        this.showIntuition = false;
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadConversationId();
        this.scrollToBottom();
    }

    setupEventListeners() {
        const sendBtn = document.getElementById('send-btn');
        const messageInput = document.getElementById('message-input');
        const intuitionToggle = document.getElementById('show-intuition');

        if (sendBtn) {
            sendBtn.addEventListener('click', () => this.sendMessage());
        }

        if (messageInput) {
            messageInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendMessage();
                }
            });
        }

        if (intuitionToggle) {
            intuitionToggle.addEventListener('change', (e) => {
                this.showIntuition = e.target.checked;
                this.updateMessageDisplay();
            });
        }
    }

    loadConversationId() {
        this.conversationId = sessionStorage.getItem('conversationId') || 
                              'conv_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        sessionStorage.setItem('conversationId', this.conversationId);
    }

    async sendMessage() {
        const input = document.getElementById('message-input');
        const text = input.value.trim();

        if (!text) return;

        // Add user message to transcript
        this.addMessageToUI(text, 'user');
        input.value = '';

        // Send to API
        try {
            const response = await fetch(`${AppUtils.API_URL}/api/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Session-ID': AppUtils.getSessionId(),
                    'X-Conversation-ID': this.conversationId
                },
                body: JSON.stringify({
                    message: text,
                    show_intuition: this.showIntuition
                })
            });

            if (!response.ok) throw new Error('API error');

            const data = await response.json();

            // Add assistant response
            this.addMessageToUI(data.response, 'assistant');

            // Update evidence panel
            this.updateEvidencePanel(data.evidence || []);

            // Store message
            this.messageTranscript.push({
                user: text,
                assistant: data.response,
                evidence: data.evidence || []
            });

        } catch (error) {
            console.error('Chat error:', error);
            AppUtils.showNotification('Failed to send message', 'error');
            this.addMessageToUI('Sorry, I encountered an error. Please try again.', 'assistant');
        }
    }

    addMessageToUI(text, role) {
        const transcript = document.getElementById('transcript');
        if (!transcript) return;

        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}`;
        
        // Simple markdown-like formatting
        let html = this.escapeHtml(text);
        html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');
        html = html.replace(/\n/g, '<br>');
        
        messageDiv.innerHTML = html;
        transcript.appendChild(messageDiv);
        this.scrollToBottom();
    }

    updateEvidencePanel(evidence) {
        const panel = document.getElementById('evidence-items');
        if (!panel) return;

        panel.innerHTML = '';

        evidence.forEach(item => {
            const div = document.createElement('div');
            div.className = 'evidence-item';
            div.innerHTML = `
                <div class="type">${this.escapeHtml(item.type)}</div>
                <div class="content">${this.escapeHtml(item.content || '')}</div>
                <div class="source">${this.escapeHtml(item.source || 'Source')}</div>
            `;
            panel.appendChild(div);
        });

        if (evidence.length === 0) {
            panel.innerHTML = '<p style="color: #999;">No evidence cited</p>';
        }
    }

    updateMessageDisplay() {
        // Placeholder for showing/hiding intuition in message display
        const messages = document.querySelectorAll('.message.assistant');
        messages.forEach(msg => {
            // Implementation depends on message structure in backend
        });
    }

    scrollToBottom() {
        const transcript = document.getElementById('transcript');
        if (transcript) {
            transcript.scrollTop = transcript.scrollHeight;
        }
    }

    escapeHtml(text) {
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return text.replace(/[&<>"']/g, m => map[m]);
    }
}

// Initialize on page load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.chatManager = new ChatManager();
    });
} else {
    window.chatManager = new ChatManager();
}
