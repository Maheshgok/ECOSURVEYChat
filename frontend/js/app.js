// Economic Survey Practitioner Chat v1.2 - Main App Logic

const API_URL = process.env.API_URL || 'http://localhost:8000';

// Navigation
document.addEventListener('DOMContentLoaded', () => {
    // Set active nav link
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('.header nav a');
    
    navLinks.forEach(link => {
        const href = link.getAttribute('href');
        if (currentPath.endsWith(href) || 
            (currentPath.endsWith('/') && href === 'index.html') ||
            (currentPath === '/' && href === 'index.html')) {
            link.classList.add('active');
        }
    });

    // Health check
    checkApiHealth();
});

// API Health Check
async function checkApiHealth() {
    try {
        const response = await fetch(`${API_URL}/health`);
        if (response.ok) {
            console.log('✓ API is healthy');
        } else {
            console.warn('⚠ API health check failed');
        }
    } catch (error) {
        console.error('✗ Cannot connect to API:', error);
    }
}

// Utilities
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 15px 20px;
        background-color: ${type === 'error' ? '#e74c3c' : type === 'success' ? '#27ae60' : '#0066cc'};
        color: white;
        border-radius: 4px;
        z-index: 1000;
        animation: slideIn 0.3s;
    `;
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Session Management
function getSessionId() {
    let sessionId = sessionStorage.getItem('sessionId');
    if (!sessionId) {
        sessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        sessionStorage.setItem('sessionId', sessionId);
    }
    return sessionId;
}

// Export for use in other scripts
window.AppUtils = {
    API_URL,
    showNotification,
    getSessionId,
    checkApiHealth
};
