import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import './Homepage.css'

function Homepage() {
  const { user } = useAuth()

  const blogPosts = [
    {
      id: 1,
      title: "Understanding Economic Survey 2026",
      excerpt: "Dive deep into the key highlights and insights from India's Economic Survey 2026. Explore fiscal policies, growth projections, and sector-wise analysis.",
      image: "https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=800&q=80",
      date: "February 5, 2026",
      readTime: "5 min read"
    },
    {
      id: 2,
      title: "AI-Powered Policy Analysis",
      excerpt: "How artificial intelligence is transforming the way we understand and analyze economic policies. Our GraphRAG technology provides cited, explainable answers.",
      image: "https://images.unsplash.com/photo-1677442136019-21780ecad995?w=800&q=80",
      date: "February 3, 2026",
      readTime: "7 min read"
    },
    {
      id: 3,
      title: "Fiscal Deficit Trends & Projections",
      excerpt: "Analyzing India's fiscal deficit trajectory from FY2023 to FY2026. Understanding the government's consolidation strategy and its implications.",
      image: "https://images.unsplash.com/photo-1579532537598-459ecdaf39cc?w=800&q=80",
      date: "January 28, 2026",
      readTime: "6 min read"
    },
    {
      id: 4,
      title: "GDP Growth: Sectoral Breakdown",
      excerpt: "A comprehensive look at sector-wise contribution to GDP growth. Agriculture, manufacturing, and services - which sectors are driving India's economy?",
      image: "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=800&q=80",
      date: "January 25, 2026",
      readTime: "8 min read"
    }
  ]

  return (
    <div className="homepage">
      {/* Hero Section */}
      <section className="hero">
        <div className="hero-content">
          <h1 className="hero-title">
            <span className="gradient-text">Economic Insights</span>
            <br />
            Powered by AI
          </h1>
          <p className="hero-subtitle">
            Chat with India's Economic Survey 2026 using advanced AI models.
            Get instant, cited answers to complex policy questions.
          </p>
          {user ? (
            <div className="hero-cta">
              <Link to="/chat" className="cta-button primary">
                Start Chatting →
              </Link>
              <Link to="/graphrag" className="cta-button secondary">
                Try GraphRAG
              </Link>
            </div>
          ) : (
            <p className="hero-login-hint">
              <strong>Sign in</strong> to access our AI chatbots and explore the Economic Survey
            </p>
          )}
        </div>
        <div className="hero-visual">
          <div className="floating-card">
            <div className="card-icon">💬</div>
            <div className="card-text">
              <strong>Standard Chat</strong>
              <span>Fast conversational AI</span>
            </div>
          </div>
          <div className="floating-card delay-1">
            <div className="card-icon">🔍</div>
            <div className="card-text">
              <strong>GraphRAG</strong>
              <span>Cited, explainable answers</span>
            </div>
          </div>
          <div className="floating-card delay-2">
            <div className="card-icon">📊</div>
            <div className="card-text">
              <strong>Data Analysis</strong>
              <span>Quantitative insights</span>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="features">
        <h2 className="section-title">Why EdgeChurn AI?</h2>
        <div className="features-grid">
          <div className="feature-card">
            <div className="feature-icon">⚡</div>
            <h3>Lightning Fast</h3>
            <p>Get answers in seconds with our optimized RAG pipeline. No more searching through 500+ page documents.</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">🎯</div>
            <h3>Highly Accurate</h3>
            <p>Our AI is trained on the complete Economic Survey 2026, providing precise, contextual responses.</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">📖</div>
            <h3>Cited Sources</h3>
            <p>Every answer includes page references and exact quotes from the source document.</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">🧠</div>
            <h3>Two AI Models</h3>
            <p>Choose between Standard Chat (fast) or GraphRAG (explainable reasoning with fact citations).</p>
          </div>
        </div>
      </section>

      {/* Blog Section */}
      <section className="blog-section">
        <h2 className="section-title">Latest Insights</h2>
        <div className="blog-grid">
          {blogPosts.map(post => (
            <article key={post.id} className="blog-card">
              <div className="blog-image" style={{ backgroundImage: `url(${post.image})` }}></div>
              <div className="blog-content">
                <div className="blog-meta">
                  <span className="blog-date">{post.date}</span>
                  <span className="blog-dot">•</span>
                  <span className="blog-read-time">{post.readTime}</span>
                </div>
                <h3 className="blog-title">{post.title}</h3>
                <p className="blog-excerpt">{post.excerpt}</p>
                <a href="#" className="blog-link">Read More →</a>
              </div>
            </article>
          ))}
        </div>
      </section>

      {/* CTA Section */}
      <section className="cta-section">
        <div className="cta-content">
          <h2>Ready to Explore?</h2>
          <p>Sign in now to start chatting with the Economic Survey AI</p>
          {!user && (
            <button className="cta-button-large">
              Get Started - It's Free
            </button>
          )}
        </div>
      </section>
    </div>
  )
}

export default Homepage
