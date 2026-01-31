-- Consolidated migration: Apply Phase 1-6 with correct schema
-- This applies core tables from 001, then overlays 002-006

-- ============================================================================
-- PHASE 1: Core Tables (from 001_init_phase1.sql)
-- ============================================================================

-- Corpora (survey collections)
CREATE TABLE corpora (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    metadata JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_corpora_is_active ON corpora(is_active);

-- Documents (PDF files)
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    corpus_id UUID NOT NULL REFERENCES corpora(id) ON DELETE CASCADE,
    filename VARCHAR(500) NOT NULL,
    title VARCHAR(500),
    
    -- File metadata
    file_hash VARCHAR(64) UNIQUE NOT NULL,
    file_size INTEGER,
    page_count INTEGER,
    
    -- Parsing status
    status VARCHAR(50) DEFAULT 'pending',
    error_message TEXT,
    
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_documents_corpus_id ON documents(corpus_id);
CREATE INDEX idx_documents_status ON documents(status);
CREATE INDEX idx_documents_file_hash ON documents(file_hash);

-- Nodes (text chunks from documents)
CREATE TABLE nodes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    corpus_id UUID NOT NULL REFERENCES corpora(id) ON DELETE CASCADE,
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    
    -- Content
    text TEXT NOT NULL,
    node_type VARCHAR(50) NOT NULL,
    
    -- Position in document
    page_number INTEGER,
    bbox JSONB,
    
    -- Content analysis
    token_count INTEGER,
    metadata JSONB DEFAULT '{}',
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_nodes_corpus_id ON nodes(corpus_id);
CREATE INDEX idx_nodes_document_id ON nodes(document_id);
CREATE INDEX idx_nodes_type ON nodes(node_type);

-- Edges (relationships between nodes)
CREATE TABLE edges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    corpus_id UUID NOT NULL REFERENCES corpora(id) ON DELETE CASCADE,
    
    source_node_id UUID NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    target_node_id UUID NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    
    edge_type VARCHAR(50) NOT NULL,
    weight NUMERIC(5,4) DEFAULT 1.0,
    
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_edges_source ON edges(source_node_id);
CREATE INDEX idx_edges_target ON edges(target_node_id);
CREATE INDEX idx_edges_type ON edges(edge_type);
CREATE INDEX idx_edges_corpus_id ON edges(corpus_id);

-- Data files (XLSX files)
CREATE TABLE data_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    corpus_id UUID NOT NULL REFERENCES corpora(id) ON DELETE CASCADE,
    filename VARCHAR(500) NOT NULL,
    
    file_hash VARCHAR(64) UNIQUE NOT NULL,
    file_size INTEGER,
    
    status VARCHAR(50) DEFAULT 'pending',
    error_message TEXT,
    
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_data_files_corpus_id ON data_files(corpus_id);
CREATE INDEX idx_data_files_status ON data_files(status);

-- Data sheets (sheets within XLSX files)
CREATE TABLE data_sheets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    data_file_id UUID NOT NULL REFERENCES data_files(id) ON DELETE CASCADE,
    corpus_id UUID NOT NULL REFERENCES corpora(id) ON DELETE CASCADE,
    
    sheet_name VARCHAR(255) NOT NULL,
    sheet_index INTEGER NOT NULL,
    
    row_count INTEGER,
    col_count INTEGER,
    
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_data_sheets_file_id ON data_sheets(data_file_id);
CREATE INDEX idx_data_sheets_corpus_id ON data_sheets(corpus_id);

-- Data tables (structured tables extracted from sheets)
CREATE TABLE data_tables (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    data_sheet_id UUID NOT NULL REFERENCES data_sheets(id) ON DELETE CASCADE,
    corpus_id UUID NOT NULL REFERENCES corpora(id) ON DELETE CASCADE,
    
    title VARCHAR(500),
    description TEXT,
    
    -- Table structure
    headers JSONB NOT NULL,
    row_count INTEGER,
    col_count INTEGER,
    
    -- Cell range in sheet
    start_row INTEGER,
    end_row INTEGER,
    start_col INTEGER,
    end_col INTEGER,
    
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_data_tables_sheet_id ON data_tables(data_sheet_id);
CREATE INDEX idx_data_tables_corpus_id ON data_tables(corpus_id);

-- Indicators (time series definitions)
CREATE TABLE indicators (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    corpus_id UUID NOT NULL REFERENCES corpora(id) ON DELETE CASCADE,
    data_table_id UUID REFERENCES data_tables(id) ON DELETE CASCADE,
    
    name VARCHAR(500) NOT NULL,
    description TEXT,
    unit VARCHAR(100),
    
    -- Categorization
    category VARCHAR(100),
    subcategory VARCHAR(100),
    
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_indicators_corpus_id ON indicators(corpus_id);
CREATE INDEX idx_indicators_table_id ON indicators(data_table_id);
CREATE INDEX idx_indicators_category ON indicators(category);

-- Indicator series (time series data points)
CREATE TABLE indicator_series (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    indicator_id UUID NOT NULL REFERENCES indicators(id) ON DELETE CASCADE,
    corpus_id UUID NOT NULL REFERENCES corpora(id) ON DELETE CASCADE,
    
    -- Time series data
    time_period VARCHAR(100) NOT NULL,
    value NUMERIC,
    
    -- Optional dimensions
    geography VARCHAR(100),
    demographic VARCHAR(100),
    
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_indicator_series_indicator_id ON indicator_series(indicator_id);
CREATE INDEX idx_indicator_series_corpus_id ON indicator_series(corpus_id);
CREATE INDEX idx_indicator_series_time_period ON indicator_series(time_period);

-- Search index (for text search)
CREATE TABLE search_index (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    corpus_id UUID NOT NULL REFERENCES corpora(id) ON DELETE CASCADE,
    node_id UUID REFERENCES nodes(id) ON DELETE CASCADE,
    
    content TEXT NOT NULL,
    content_vector tsvector,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_search_corpus_id ON search_index(corpus_id);
CREATE INDEX idx_search_vector ON search_index USING gin(content_vector);

-- Embeddings (vector embeddings for semantic search)
CREATE TABLE embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    corpus_id UUID NOT NULL REFERENCES corpora(id) ON DELETE CASCADE,
    node_id UUID REFERENCES nodes(id) ON DELETE CASCADE,
    
    embedding NUMERIC[] NOT NULL,
    model_name VARCHAR(100) NOT NULL,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_embeddings_corpus_id ON embeddings(corpus_id);
CREATE INDEX idx_embeddings_node_id ON embeddings(node_id);

-- ============================================================================
-- PHASE 2: OAuth Tables (from 002_add_auth_tables.sql)
-- ============================================================================

-- Users table for OAuth authentication
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    google_id VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    picture VARCHAR(500),
    email_verified BOOLEAN DEFAULT FALSE,
    
    -- Login tracking
    first_login TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_google_id ON users(google_id);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_is_active ON users(is_active);

-- Sessions table for session management (Phase 2 version with user_id UUID)
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token VARCHAR(500) UNIQUE NOT NULL,
    
    -- Session metadata
    ip_address VARCHAR(45),
    user_agent VARCHAR(500),
    
    -- Session tracking
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    is_active BOOLEAN DEFAULT TRUE
);

CREATE INDEX idx_sessions_token ON sessions(token);
CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_is_active ON sessions(is_active);
CREATE INDEX idx_sessions_expires_at ON sessions(expires_at);

-- Conversations (Phase 2 version with user_id)
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    corpus_id UUID NOT NULL REFERENCES corpora(id) ON DELETE CASCADE,
    
    title VARCHAR(500),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_conversations_user_id ON conversations(user_id);
CREATE INDEX idx_conversations_corpus_id ON conversations(corpus_id);

-- Messages (chat messages)
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX idx_messages_created_at ON messages(created_at);

-- Retrieval events (Phase 2 version with user_id and array)
CREATE TABLE retrieval_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    query TEXT NOT NULL,
    retrieved_node_ids UUID[] DEFAULT '{}',
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_retrieval_events_conversation_id ON retrieval_events(conversation_id);
CREATE INDEX idx_retrieval_events_user_id ON retrieval_events(user_id);

-- ============================================================================
-- PHASE 3: Ingestion Tables (from 003_add_ingestion_tables.sql)
-- ============================================================================

CREATE TABLE ingestion_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    corpus_id UUID NOT NULL REFERENCES corpora(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    
    run_type VARCHAR(50) NOT NULL CHECK (run_type IN ('pdf', 'xlsx', 'full')),
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'failed')),
    
    -- Stats
    documents_processed INTEGER DEFAULT 0,
    documents_failed INTEGER DEFAULT 0,
    nodes_created INTEGER DEFAULT 0,
    
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,
    
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_ingestion_runs_corpus_id ON ingestion_runs(corpus_id);
CREATE INDEX idx_ingestion_runs_status ON ingestion_runs(status);
CREATE INDEX idx_ingestion_runs_user_id ON ingestion_runs(user_id);

-- ============================================================================
-- PHASE 4: Data Storage Tables (from 004_add_data_storage.sql)
-- ============================================================================

CREATE TABLE data_rows (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    data_table_id UUID NOT NULL REFERENCES data_tables(id) ON DELETE CASCADE,
    corpus_id UUID NOT NULL REFERENCES corpora(id) ON DELETE CASCADE,
    
    row_index INTEGER NOT NULL,
    values JSONB NOT NULL,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_data_rows_table_id ON data_rows(data_table_id);
CREATE INDEX idx_data_rows_corpus_id ON data_rows(corpus_id);

-- ============================================================================
-- PHASE 5: Insights Tables (from 005_add_insights.sql)
-- ============================================================================

-- Message labels (for analytics)
CREATE TABLE message_labels (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    
    label VARCHAR(100) NOT NULL,
    confidence NUMERIC(5,4),
    
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_message_labels_conversation_id ON message_labels(conversation_id);
CREATE INDEX idx_message_labels_label ON message_labels(label);

-- Topic clusters (for analytics)
CREATE TABLE topic_clusters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    corpus_id UUID NOT NULL REFERENCES corpora(id) ON DELETE CASCADE,
    
    topic_name VARCHAR(255) NOT NULL,
    message_ids UUID[] DEFAULT '{}',
    
    centroid NUMERIC[] NOT NULL,
    size INTEGER DEFAULT 0,
    
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_topic_clusters_corpus_id ON topic_clusters(corpus_id);

-- Daily insights (for admin dashboard)
CREATE TABLE daily_insights (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    corpus_id UUID NOT NULL REFERENCES corpora(id) ON DELETE CASCADE,
    
    insight_date DATE NOT NULL,
    total_conversations INTEGER DEFAULT 0,
    total_messages INTEGER DEFAULT 0,
    unique_users INTEGER DEFAULT 0,
    
    top_topics JSONB DEFAULT '[]',
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_daily_insights_corpus_id ON daily_insights(corpus_id);
CREATE INDEX idx_daily_insights_date ON daily_insights(insight_date);

-- Views and functions for insights
CREATE OR REPLACE FUNCTION count_table_rows(table_id UUID)
RETURNS INTEGER AS $$
DECLARE
    row_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO row_count FROM data_rows WHERE data_table_id = table_id;
    RETURN row_count;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION find_duplicate_rows(table_id UUID)
RETURNS TABLE(row_values JSONB, row_count BIGINT) AS $$
BEGIN
    RETURN QUERY
    SELECT dr.values, COUNT(*) as row_count
    FROM data_rows dr
    WHERE dr.data_table_id = table_id
    GROUP BY dr.values
    HAVING COUNT(*) > 1;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION update_data_file_row_count()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE data_files
    SET updated_at = CURRENT_TIMESTAMP
    WHERE id IN (
        SELECT ds.data_file_id
        FROM data_sheets ds
        JOIN data_tables dt ON dt.data_sheet_id = ds.id
        WHERE dt.id = NEW.data_table_id
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- PHASE 6: Summaries Tables (from 006_add_summaries.sql)
-- ============================================================================

-- Topic briefs (narrative summaries for topics)
CREATE TABLE topic_briefs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    corpus_id UUID NOT NULL REFERENCES corpora(id) ON DELETE CASCADE,
    
    topic VARCHAR(255) NOT NULL,
    summary TEXT NOT NULL,
    
    linked_node_ids UUID[] DEFAULT '{}',
    linked_series_ids UUID[] DEFAULT '{}',
    
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_topic_briefs_corpus_id ON topic_briefs(corpus_id);
CREATE INDEX idx_topic_briefs_topic ON topic_briefs(topic);

-- Claim cards (evidence-backed claims)
CREATE TABLE claim_cards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    corpus_id UUID NOT NULL REFERENCES corpora(id) ON DELETE CASCADE,
    
    topic VARCHAR(255) NOT NULL,
    claim_text TEXT NOT NULL,
    
    evidence_node_ids UUID[] DEFAULT '{}',
    evidence_series_ids UUID[] DEFAULT '{}',
    
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_claim_cards_corpus_id ON claim_cards(corpus_id);
CREATE INDEX idx_claim_cards_topic ON claim_cards(topic);

-- Legacy tables (backwards compatibility)
CREATE TABLE insights (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    corpus_id UUID NOT NULL REFERENCES corpora(id) ON DELETE CASCADE,
    
    insight_type VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE summaries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    corpus_id UUID NOT NULL REFERENCES corpora(id) ON DELETE CASCADE,
    
    summary_type VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE insight_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    insight_id UUID REFERENCES insights(id) ON DELETE CASCADE,
    summary_id UUID REFERENCES summaries(id) ON DELETE CASCADE,
    
    embedding NUMERIC[] NOT NULL,
    model_name VARCHAR(100) NOT NULL,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Functions for summaries
CREATE OR REPLACE FUNCTION update_topic_briefs_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER topic_briefs_update_timestamp
BEFORE UPDATE ON topic_briefs
FOR EACH ROW EXECUTE FUNCTION update_topic_briefs_timestamp();

CREATE OR REPLACE FUNCTION update_claim_cards_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER claim_cards_update_timestamp
BEFORE UPDATE ON claim_cards
FOR EACH ROW EXECUTE FUNCTION update_claim_cards_timestamp();

-- Completion message
SELECT 'All migrations (Phase 1-6) applied successfully' as status;
