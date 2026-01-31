// Summary Page Logic

class SummaryManager {
    constructor() {
        this.corpusId = this.getCorpusId();
        this.briefingData = null;
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadBriefing();
    }

    setupEventListeners() {
        // Expand/collapse topic cards
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('topic-card')) {
                this.toggleTopicCard(e.target);
            }
        });

        // Evidence drawer toggle
        const evidenceBtn = document.getElementById('show-evidence-btn');
        if (evidenceBtn) {
            evidenceBtn.addEventListener('click', () => {
                this.toggleEvidenceDrawer();
            });
        }
    }

    getCorpusId() {
        const params = new URLSearchParams(window.location.search);
        return params.get('corpus_id') || 'default';
    }

    async loadBriefing() {
        try {
            const response = await fetch(
                `${AppUtils.API_URL}/corpus/${this.corpusId}/briefing`,
                {
                    headers: {
                        'X-Session-ID': AppUtils.getSessionId()
                    }
                }
            );

            if (!response.ok) throw new Error('Failed to load briefing');

            this.briefingData = await response.json();
            this.renderBriefing();

        } catch (error) {
            console.error('Briefing load error:', error);
            AppUtils.showNotification('Failed to load briefing', 'error');
            this.renderPlaceholder();
        }
    }

    renderBriefing() {
        if (!this.briefingData) return;

        // Render topline bullets
        const toplineSection = document.getElementById('topline-bullets');
        if (toplineSection && this.briefingData.topline) {
            toplineSection.innerHTML = '';
            this.briefingData.topline.forEach(bullet => {
                const li = document.createElement('li');
                li.textContent = bullet;
                toplineSection.appendChild(li);
            });
        }

        // Render topic briefs
        const topicsContainer = document.getElementById('topics-container');
        if (topicsContainer && this.briefingData.topic_briefs) {
            topicsContainer.innerHTML = '';
            this.briefingData.topic_briefs.forEach(brief => {
                const card = this.createTopicCard(brief);
                topicsContainer.appendChild(card);
            });
        }

        // Render key numbers
        const numbersContainer = document.getElementById('key-numbers');
        if (numbersContainer && this.briefingData.key_numbers) {
            numbersContainer.innerHTML = '';
            this.briefingData.key_numbers.forEach(num => {
                const chip = document.createElement('div');
                chip.className = 'number-chip';
                chip.innerHTML = `
                    <div class="value">${this.escapeHtml(num.value)}</div>
                    <div class="label">${this.escapeHtml(num.label)}</div>
                `;
                numbersContainer.appendChild(chip);
            });
        }
    }

    createTopicCard(brief) {
        const card = document.createElement('div');
        card.className = 'topic-card';
        card.innerHTML = `
            <div style="font-weight: 600; margin-bottom: 8px;">
                ${this.escapeHtml(brief.title)}
            </div>
            <div class="brief-content" style="display: none; font-size: 14px;">
                ${this.escapeHtml(brief.content)}
            </div>
            <div style="color: #0066cc; font-size: 12px; margin-top: 8px;">
                Evidence: ${brief.evidence_count || 0} items
            </div>
        `;
        card.dataset.briefId = brief.id;
        return card;
    }

    toggleTopicCard(card) {
        const content = card.querySelector('.brief-content');
        if (content) {
            const isVisible = content.style.display !== 'none';
            content.style.display = isVisible ? 'none' : 'block';
            card.style.backgroundColor = isVisible ? 'var(--light-color)' : '#d5dbf5';
        }
    }

    toggleEvidenceDrawer() {
        const drawer = document.getElementById('evidence-drawer');
        if (drawer) {
            const isVisible = drawer.style.display !== 'none';
            drawer.style.display = isVisible ? 'none' : 'block';
        }
    }

    renderPlaceholder() {
        const main = document.querySelector('.main');
        if (main) {
            main.innerHTML = `
                <div style="text-align: center; padding: 40px;">
                    <p>Unable to load briefing. Please try again later.</p>
                </div>
            `;
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
        return String(text).replace(/[&<>"']/g, m => map[m]);
    }
}

// Initialize on page load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.summaryManager = new SummaryManager();
    });
} else {
    window.summaryManager = new SummaryManager();
}
