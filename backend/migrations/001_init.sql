-- Economic Survey Practitioner Chat v1.2
-- Database Schema (PostgreSQL 15+)
-- Created: January 30, 2026

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

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
    year INTEGER,
    volume INTEGER,
    role VARCHAR(20) NOT NULL CHECK (role IN ('primary', 'supplement')),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_documents_corpus_id ON documents(corpus_id);
CREATE INDEX idx_documents_role ON documents(role);

-- Nodes: Evidence units (sections, paragraphs, boxes, tables, charts)
CREATE TABLE IF NOT EXISTS nodes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    node_type VARCHAR(50) NOT NULL,  -- 'section', 'paragraph', 'box', 'table', 'chart', 'image'
    label VARCHAR(255),              -- e.g., "Box I.2", "Table I.2a", "Chart I.21"
    title VARCHAR(255),
    text TEXT,
    page_start INTEGER,
    page_end INTEGER,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_nodes_document_id ON nodes(document_id);
CREATE INDEX idx_nodes_node_type ON nodes(node_type);
CREATE INDEX idx_nodes_label ON nodes(label);

-- Edges: Relationships between nodes
CREATE TABLE IF NOT EXISTS edges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    src_node_id UUID NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    rel_type VARCHAR(20) NOT NULL CHECK (rel_type IN ('contains', 'refers_to', 'supports')),
    dst_node_id UUID NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    confidence FLOAT DEFAULT 1.0,
    evidence TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_edges_src_node ON edges(src_node_id);
CREATE INDEX idx_edges_dst_node ON edges(dst_node_id);
CREATE INDEX idx_edges_rel_type ON edges(rel_type);
CREATE INDEX idx_edges_document_id ON edges(document_id);

-- ============================================================================
-- DATASET TABLES (XLSX)
-- ============================================================================

-- Data files: XLSX workbooks
CREATE TABLE IF NOT EXISTS data_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    corpus_id UUID NOT NULL REFERENCES corpora(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    path TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_data_files_corpus_id ON data_files(corpus_id);

-- Data sheets: Individual sheets within workbooks
CREATE TABLE IF NOT EXISTS data_sheets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    file_id UUID NOT NULL REFERENCES data_files(id) ON DELETE CASCADE,
    sheet_name VARCHAR(255) NOT NULL,
    sheet_index INTEGER NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_data_sheets_file_id ON data_sheets(file_id);

-- Data tables: Extracted tables from sheets (with panel splitting)
CREATE TABLE IF NOT EXISTS data_tables (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    file_id UUID NOT NULL REFERENCES data_files(id) ON DELETE CASCADE,
    sheet_id UUID NOT NULL REFERENCES data_sheets(id) ON DELETE CASCADE,
    title VARCHAR(255),
    table_name VARCHAR(255) NOT NULL,
    range_a1 VARCHAR(50),              -- e.g., "A1:F100"
    header_rows INTEGER DEFAULT 1,
    index_cols SMALLINT DEFAULT 1,
    units VARCHAR(255),
    notes TEXT,
    table_json JSONB,                  -- Full table structure
    table_long JSONB,                  -- Long-format records: [{time, geo, indicator, measure, value, unit, provenance}, ...]
    tags TEXT[],
    confidence FLOAT DEFAULT 1.0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_data_tables_file_id ON data_tables(file_id);
CREATE INDEX idx_data_tables_sheet_id ON data_tables(sheet_id);
CREATE INDEX idx_data_tables_title ON data_tables(title);

-- ============================================================================
-- INDICATORS & DERIVED METRICS
-- ============================================================================

-- Indicators: Named metrics (e.g., "GDP Growth", "Inflation Rate")
CREATE TABLE IF NOT EXISTS indicators (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    corpus_id UUID NOT NULL REFERENCES corpora(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    aliases TEXT[],
    topic VARCHAR(100),                -- e.g., "Growth & Demand", "Inflation & Rates"
    unit VARCHAR(50),                  -- e.g., "%", "Crores INR"
    freq VARCHAR(20),                  -- e.g., "annual", "quarterly"
    geo_level VARCHAR(50),             -- e.g., "national", "state"
    definition TEXT,
    provenance VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_indicators_corpus_id ON indicators(corpus_id);
CREATE INDEX idx_indicators_topic ON indicators(topic);

-- Indicator series: Time series for indicators with derived metrics
CREATE TABLE IF NOT EXISTS indicator_series (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    indicator_id UUID NOT NULL REFERENCES indicators(id) ON DELETE CASCADE,
    geo_key VARCHAR(100),              -- e.g., "IND", "MH"
    time_start VARCHAR(20),
    time_end VARCHAR(20),
    points JSONB,                      -- [{time, value}, {time, value}, ...]
    derived_views JSONB,               -- {yoy: [...], cagr_3y: [...], cagr_5y: [...], ranks: [...]}
    provenance VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_indicator_series_indicator_id ON indicator_series(indicator_id);
CREATE INDEX idx_indicator_series_geo_key ON indicator_series(geo_key);

-- ============================================================================
-- SUMMARIES & CLAIMS
-- ============================================================================

-- Topic briefs: 3-5 minute summaries per topic
CREATE TABLE IF NOT EXISTS topic_briefs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    corpus_id UUID NOT NULL REFERENCES corpora(id) ON DELETE CASCADE,
    topic VARCHAR(100) NOT NULL,       -- e.g., "Growth & Demand"
    bullets TEXT[],                    -- 5-8 bullet points
    key_numbers JSONB,                 -- [{value, unit, label, evidence_node_ids, evidence_series_ids}, ...]
    linked_node_ids UUID[],
    linked_series_ids UUID[],
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_topic_briefs_corpus_id ON topic_briefs(corpus_id);
CREATE INDEX idx_topic_briefs_topic ON topic_briefs(topic);

-- Claim cards: Practitioner-quality claims with evidence
CREATE TABLE IF NOT EXISTS claim_cards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    corpus_id UUID NOT NULL REFERENCES corpora(id) ON DELETE CASCADE,
    topic VARCHAR(100) NOT NULL,
    claim_text TEXT NOT NULL,          -- One-sentence claim
    explanation TEXT,                  -- Practitioner tone explanation
    evidence_node_ids UUID[],          -- Must have ≥1 evidence
    evidence_series_ids UUID[],
    confidence FLOAT DEFAULT 0.9,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_claim_cards_corpus_id ON claim_cards(corpus_id);
CREATE INDEX idx_claim_cards_topic ON claim_cards(topic);

-- ============================================================================
-- SEARCH & EMBEDDINGS
-- ============================================================================

-- Full-text search index
CREATE TABLE IF NOT EXISTS search_index (
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    node_id UUID NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    raw_text TEXT NOT NULL,
    tsv TSVECTOR,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (document_id, node_id)
);

CREATE INDEX idx_search_index_tsv ON search_index USING GIN(tsv);
CREATE INDEX idx_search_index_node_id ON search_index(node_id);

-- Embeddings: Vector representations for semantic search
CREATE TABLE IF NOT EXISTS embeddings (
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    node_id UUID NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    embedded_text TEXT NOT NULL,
    embedding vector(1536),             -- For OpenAI text-embedding-3-large
    model_id VARCHAR(50),               -- e.g., "text-embedding-3-large"
    source_hash VARCHAR(64),            -- SHA256 of embedded_text for reproducibility
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (document_id, node_id)
);

CREATE INDEX idx_embeddings_node_id ON embeddings(node_id);
CREATE INDEX idx_embeddings_embedding ON embeddings USING IVFFLAT (embedding vector_cosine_ops);
CREATE INDEX idx_embeddings_model_id ON embeddings(model_id);

-- ============================================================================
-- ANALYTICS
-- ============================================================================

-- User sessions (pseudonymous only)
CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_pseudo_id VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_activity TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_sessions_user_pseudo_id ON sessions(user_pseudo_id);

-- Conversations: Chat sessions
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    corpus_id UUID NOT NULL REFERENCES corpora(id) ON DELETE CASCADE,
    session_id UUID REFERENCES sessions(id) ON DELETE SET NULL,
    user_pseudo_id VARCHAR(64) NOT NULL,
    session_metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_conversations_corpus_id ON conversations(corpus_id);
CREATE INDEX idx_conversations_user_pseudo_id ON conversations(user_pseudo_id);
CREATE INDEX idx_conversations_session_id ON conversations(session_id);

-- Messages: Chat messages
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX idx_messages_role ON messages(role);

-- Retrieval events: What evidence was retrieved for each message
CREATE TABLE IF NOT EXISTS retrieval_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    message_id UUID NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    retrieved_node_ids UUID[],
    retrieved_series_ids UUID[],
    used_evidence JSONB,               -- Final citations used in response
    latency_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_retrieval_events_conversation_id ON retrieval_events(conversation_id);
CREATE INDEX idx_retrieval_events_message_id ON retrieval_events(message_id);

-- Message labels: Offline classification
CREATE TABLE IF NOT EXISTS message_labels (
    message_id UUID NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    topics TEXT[],
    entities TEXT[],
    intent VARCHAR(50),                -- e.g., "question", "clarification", "challenge", "request", "feedback"
    sentiment VARCHAR(20),             -- e.g., "optimistic", "neutral", "pessimistic", "mixed"
    concerns TEXT[],
    confidence FLOAT,
    label_version VARCHAR(20),         -- For versioning labeling logic
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (message_id)
);

CREATE INDEX idx_message_labels_created_at ON message_labels(created_at);

-- Topic clusters: Weekly clustering of user questions
CREATE TABLE IF NOT EXISTS topic_clusters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    corpus_id UUID NOT NULL REFERENCES corpora(id) ON DELETE CASCADE,
    cluster_id INTEGER,
    date_range VARCHAR(50),            -- e.g., "2026-01-27 to 2026-02-02"
    topic VARCHAR(255),
    summary TEXT,
    example_message_ids UUID[],
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_topic_clusters_corpus_id ON topic_clusters(corpus_id);
CREATE INDEX idx_topic_clusters_created_at ON topic_clusters(created_at);

-- Daily insights: Aggregated metrics
CREATE TABLE IF NOT EXISTS daily_insights (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    corpus_id UUID NOT NULL REFERENCES corpora(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    total_questions INTEGER DEFAULT 0,
    top_topics TEXT[],
    top_concerns TEXT[],
    sentiment_mix JSONB,               -- {optimistic: int, neutral: int, pessimistic: int, mixed: int}
    notable_questions TEXT[],
    coverage_gaps TEXT[],              -- Questions with low evidence coverage
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (corpus_id, date)
);

CREATE INDEX idx_daily_insights_corpus_id ON daily_insights(corpus_id);
CREATE INDEX idx_daily_insights_date ON daily_insights(date);

-- ============================================================================
-- INGESTION METADATA
-- ============================================================================

-- Track ingestion runs for idempotency
CREATE TABLE IF NOT EXISTS ingestion_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    corpus_id UUID NOT NULL REFERENCES corpora(id) ON DELETE CASCADE,
    stage VARCHAR(50),                 -- e.g., "pdf_ingest", "xlsx_ingest", "indicators", "summaries"
    status VARCHAR(20),                -- e.g., "started", "completed", "failed"
    error_message TEXT,
    items_processed INTEGER DEFAULT 0,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_ingestion_runs_corpus_id ON ingestion_runs(corpus_id);
CREATE INDEX idx_ingestion_runs_stage ON ingestion_runs(stage);
CREATE INDEX idx_ingestion_runs_status ON ingestion_runs(status);
