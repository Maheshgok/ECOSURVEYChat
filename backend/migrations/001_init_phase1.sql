-- Economic Survey Practitioner Chat v1.2
-- Database Schema (PostgreSQL 15) - Phase 1 Simplified Version
-- (pgvector extension optional - schema uses TEXT for embeddings in Phase 1)
-- Created: January 31, 2026

-- Optional pgvector extension (if installed)
-- CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================================
-- CORE TABLES
-- ============================================================================

-- Corpora: Collections of documents (Survey + supplements + datasets)
CREATE TABLE IF NOT EXISTS corpora (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Documents: PDFs, XLSX, HTML, supplements
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    corpus_id UUID NOT NULL REFERENCES corpora(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    file_path VARCHAR(512),
    file_type VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_documents_corpus_id ON documents(corpus_id);

-- Nodes: Evidence nodes (text excerpts with location references)
CREATE TABLE IF NOT EXISTS nodes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    node_type VARCHAR(50),
    content TEXT NOT NULL,
    page_number INT,
    section_name VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_nodes_document_id ON nodes(document_id);

-- Edges: Evidence relationships
CREATE TABLE IF NOT EXISTS edges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_node_id UUID NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    target_node_id UUID NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    rel_type VARCHAR(50) NOT NULL CHECK (rel_type IN ('contains', 'refers_to', 'supports')),
    weight DECIMAL(3,2) DEFAULT 1.0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_edges_source_node ON edges(source_node_id);
CREATE INDEX IF NOT EXISTS idx_edges_target_node ON edges(target_node_id);

-- ============================================================================
-- DATASET TABLES
-- ============================================================================

-- Data Files: Uploaded XLSX/CSV files
CREATE TABLE IF NOT EXISTS data_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    corpus_id UUID NOT NULL REFERENCES corpora(id) ON DELETE CASCADE,
    file_name VARCHAR(255) NOT NULL,
    file_path VARCHAR(512),
    file_type VARCHAR(50),
    ingestion_run_id UUID,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_data_files_corpus_id ON data_files(corpus_id);

-- Data Sheets: Sheets within files
CREATE TABLE IF NOT EXISTS data_sheets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    data_file_id UUID NOT NULL REFERENCES data_files(id) ON DELETE CASCADE,
    sheet_name VARCHAR(255) NOT NULL,
    row_count INT,
    column_count INT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_data_sheets_file_id ON data_sheets(data_file_id);

-- Data Tables: Panel tables from sheets
CREATE TABLE IF NOT EXISTS data_tables (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    data_sheet_id UUID NOT NULL REFERENCES data_sheets(id) ON DELETE CASCADE,
    table_name VARCHAR(255) NOT NULL,
    table_long JSONB,  -- Long-form representation
    derived_views JSONB,  -- Panel views (country, region, etc.)
    row_dimension VARCHAR(100),
    column_dimension VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_data_tables_sheet_id ON data_tables(data_sheet_id);

-- Indicators: Derived metrics (year/region aggregates)
CREATE TABLE IF NOT EXISTS indicators (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    data_table_id UUID NOT NULL REFERENCES data_tables(id) ON DELETE CASCADE,
    indicator_name VARCHAR(255) NOT NULL,
    unit VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_indicators_table_id ON indicators(data_table_id);

-- Indicator Series: Time series of indicators
CREATE TABLE IF NOT EXISTS indicator_series (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    indicator_id UUID NOT NULL REFERENCES indicators(id) ON DELETE CASCADE,
    period VARCHAR(50),  -- Year, quarter, month
    value DECIMAL(15,4),
    region VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_indicator_series_indicator_id ON indicator_series(indicator_id);

-- ============================================================================
-- SUMMARY TABLES
-- ============================================================================

-- Topic Briefs: Executive summaries with supporting evidence
CREATE TABLE IF NOT EXISTS topic_briefs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    corpus_id UUID NOT NULL REFERENCES corpora(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    evidence_nodes JSONB,  -- Links to supporting node IDs
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_topic_briefs_corpus_id ON topic_briefs(corpus_id);

-- Claim Cards: Factual claims with evidence links
CREATE TABLE IF NOT EXISTS claim_cards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    corpus_id UUID NOT NULL REFERENCES corpora(id) ON DELETE CASCADE,
    claim_text TEXT NOT NULL,
    evidence_node_id UUID REFERENCES nodes(id) ON DELETE SET NULL,
    confidence DECIMAL(3,2),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_claim_cards_corpus_id ON claim_cards(corpus_id);

-- Search Index: Full-text search index
CREATE TABLE IF NOT EXISTS search_index (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    node_id UUID NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    tsv TSVECTOR,  -- Text search vector
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_search_index_tsv ON search_index USING GIN(tsv);
CREATE INDEX IF NOT EXISTS idx_search_index_node_id ON search_index(node_id);

-- Embeddings: OpenAI embeddings for semantic search
CREATE TABLE IF NOT EXISTS embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    node_id UUID NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    embedding_model VARCHAR(100),
    embedding_dim INT,
    embedding_value TEXT,  -- Phase 1: Store as JSON text
    -- embedding_value vector(1536),  -- Phase 2+: Use pgvector after installed
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_embeddings_node_id ON embeddings(node_id);

-- ============================================================================
-- ANALYTICS TABLES
-- ============================================================================

-- Sessions: User sessions (pseudonymous)
CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id_hash VARCHAR(256),  -- SHA256(google_sub + SERVER_SALT)
    session_start TIMESTAMPTZ DEFAULT NOW(),
    session_end TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sessions_user_id_hash ON sessions(user_id_hash);

-- Conversations: Multi-turn conversations
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    corpus_id UUID NOT NULL REFERENCES corpora(id) ON DELETE CASCADE,
    start_time TIMESTAMPTZ DEFAULT NOW(),
    end_time TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_conversations_session_id ON conversations(session_id);
CREATE INDEX IF NOT EXISTS idx_conversations_corpus_id ON conversations(corpus_id);

-- Messages: Individual messages in conversations
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    token_count INT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id);

-- Retrieval Events: Evidence retrieval tracking
CREATE TABLE IF NOT EXISTS retrieval_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id UUID NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    retrieved_node_id UUID REFERENCES nodes(id) ON DELETE SET NULL,
    relevance_score DECIMAL(3,2),
    rank_position INT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_retrieval_events_message_id ON retrieval_events(message_id);
CREATE INDEX IF NOT EXISTS idx_retrieval_events_node_id ON retrieval_events(retrieved_node_id);

-- Message Labels: Human labels for model outputs
CREATE TABLE IF NOT EXISTS message_labels (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id UUID NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    sentiment VARCHAR(50) CHECK (sentiment IN ('positive', 'negative', 'neutral', 'confused', 'error')),
    intent VARCHAR(50),
    is_correct BOOLEAN,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_message_labels_message_id ON message_labels(message_id);

-- Topic Clusters: Offline topic aggregation
CREATE TABLE IF NOT EXISTS topic_clusters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    corpus_id UUID NOT NULL REFERENCES corpora(id) ON DELETE CASCADE,
    cluster_name VARCHAR(255),
    message_ids JSONB,
    centroid TEXT,  -- Topic centroid description
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_topic_clusters_corpus_id ON topic_clusters(corpus_id);

-- Daily Insights: Daily aggregated analytics
CREATE TABLE IF NOT EXISTS daily_insights (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    corpus_id UUID NOT NULL REFERENCES corpora(id) ON DELETE CASCADE,
    insight_date DATE NOT NULL,
    top_questions JSONB,
    most_cited_evidence JSONB,
    user_count INT,
    conversation_count INT,
    message_count INT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_daily_insights_corpus_id ON daily_insights(corpus_id);

-- ============================================================================
-- INGESTION TRACKING
-- ============================================================================

-- Ingestion Runs: Track idempotent ingestion
CREATE TABLE IF NOT EXISTS ingestion_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    corpus_id UUID NOT NULL REFERENCES corpora(id) ON DELETE CASCADE,
    ingestion_type VARCHAR(50) CHECK (ingestion_type IN ('xlsx', 'pdf', 'csv', 'html')),
    file_path VARCHAR(512),
    file_hash VARCHAR(256),
    status VARCHAR(50) CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    error_message TEXT,
    processed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ingestion_runs_corpus_id ON ingestion_runs(corpus_id);
CREATE INDEX IF NOT EXISTS idx_ingestion_runs_status ON ingestion_runs(status);

-- ============================================================================
-- SCHEMA INITIALIZATION COMPLETE
-- ============================================================================
-- Total Tables: 21
-- All foreign keys and indexes created
-- Ready for Phase 1 testing
