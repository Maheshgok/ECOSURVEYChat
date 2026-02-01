-- =====================================================================
-- SUPABASE MIGRATION SCRIPT
-- Run this in: Supabase Dashboard → SQL Editor → New Query
-- =====================================================================

-- Enable pgvector extension first
CREATE EXTENSION IF NOT EXISTS vector;

-- =====================================================================
-- Migration 001: Initial Schema
-- =====================================================================

-- Phase 1: Core data tracking
CREATE TABLE IF NOT EXISTS corpuses (
    corpus_id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS documents (
    document_id SERIAL PRIMARY KEY,
    corpus_id INT REFERENCES corpuses(corpus_id) ON DELETE CASCADE,
    title VARCHAR(500),
    doc_type VARCHAR(100),
    year INT,
    source_url TEXT,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    file_size_bytes BIGINT,
    file_path TEXT
);

CREATE TABLE IF NOT EXISTS chunks (
    chunk_id SERIAL PRIMARY KEY,
    document_id INT REFERENCES documents(document_id) ON DELETE CASCADE,
    chunk_index INT NOT NULL,
    content TEXT NOT NULL,
    token_count INT,
    embedding vector(3072),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_chunks_document ON chunks(document_id);
-- Note: Vector index will be created later after data ingestion
-- Supabase pgvector indexes are limited to 2000 dimensions
-- We use 3072-dim embeddings, so we'll create index programmatically or use brute-force search

-- =====================================================================
-- Migration 002: Authentication Tables
-- =====================================================================

CREATE TABLE IF NOT EXISTS users (
    user_id SERIAL PRIMARY KEY,
    firebase_uid VARCHAR(128) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    display_name VARCHAR(255),
    photo_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    role VARCHAR(50) DEFAULT 'user'
);

CREATE INDEX IF NOT EXISTS idx_users_firebase_uid ON users(firebase_uid);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

CREATE TABLE IF NOT EXISTS sessions (
    session_id VARCHAR(255) PRIMARY KEY,
    user_id INT REFERENCES users(user_id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_agent TEXT,
    ip_address INET
);

CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_expires ON sessions(expires_at);

-- =====================================================================
-- Migration 003: Ingestion Tables
-- =====================================================================

CREATE TABLE IF NOT EXISTS ingestion_jobs (
    job_id SERIAL PRIMARY KEY,
    corpus_id INT REFERENCES corpuses(corpus_id) ON DELETE CASCADE,
    status VARCHAR(50) DEFAULT 'pending',
    total_documents INT DEFAULT 0,
    processed_documents INT DEFAULT 0,
    failed_documents INT DEFAULT 0,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,
    config JSONB
);

CREATE INDEX IF NOT EXISTS idx_ingestion_jobs_status ON ingestion_jobs(status);
CREATE INDEX IF NOT EXISTS idx_ingestion_jobs_corpus ON ingestion_jobs(corpus_id);

CREATE TABLE IF NOT EXISTS embedding_queue (
    queue_id SERIAL PRIMARY KEY,
    chunk_id INT REFERENCES chunks(chunk_id) ON DELETE CASCADE,
    status VARCHAR(50) DEFAULT 'pending',
    retry_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP,
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_embedding_queue_status ON embedding_queue(status);

-- =====================================================================
-- Migration 004: Data Storage Tables
-- =====================================================================

CREATE TABLE IF NOT EXISTS datasets (
    dataset_id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    source VARCHAR(200),
    year_range VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB
);

CREATE TABLE IF NOT EXISTS indicators (
    indicator_id SERIAL PRIMARY KEY,
    dataset_id INT REFERENCES datasets(dataset_id) ON DELETE CASCADE,
    indicator_code VARCHAR(100) UNIQUE NOT NULL,
    indicator_name VARCHAR(500) NOT NULL,
    unit VARCHAR(100),
    description TEXT,
    metadata JSONB
);

CREATE INDEX IF NOT EXISTS idx_indicators_dataset ON indicators(dataset_id);
CREATE INDEX IF NOT EXISTS idx_indicators_code ON indicators(indicator_code);

CREATE TABLE IF NOT EXISTS time_series (
    series_id SERIAL PRIMARY KEY,
    indicator_id INT REFERENCES indicators(indicator_id) ON DELETE CASCADE,
    year INT NOT NULL,
    value NUMERIC(20, 4),
    region VARCHAR(100),
    metadata JSONB,
    UNIQUE(indicator_id, year, region)
);

CREATE INDEX IF NOT EXISTS idx_time_series_indicator ON time_series(indicator_id);
CREATE INDEX IF NOT EXISTS idx_time_series_year ON time_series(year);

-- =====================================================================
-- Migration 005: Insights Tables
-- =====================================================================

CREATE TABLE IF NOT EXISTS conversations (
    conversation_id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(user_id) ON DELETE CASCADE,
    title VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_archived BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id);

CREATE TABLE IF NOT EXISTS messages (
    message_id SERIAL PRIMARY KEY,
    conversation_id INT REFERENCES conversations(conversation_id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    tokens_used INT,
    model VARCHAR(100),
    metadata JSONB
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);

CREATE TABLE IF NOT EXISTS citations (
    citation_id SERIAL PRIMARY KEY,
    message_id INT REFERENCES messages(message_id) ON DELETE CASCADE,
    chunk_id INT REFERENCES chunks(chunk_id) ON DELETE SET NULL,
    relevance_score FLOAT,
    cited_text TEXT,
    page_number INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_citations_message ON citations(message_id);
CREATE INDEX IF NOT EXISTS idx_citations_chunk ON citations(chunk_id);

-- =====================================================================
-- Migration 006: Summaries Tables
-- =====================================================================

CREATE TABLE IF NOT EXISTS summaries (
    summary_id SERIAL PRIMARY KEY,
    document_id INT REFERENCES documents(document_id) ON DELETE CASCADE,
    summary_type VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    token_count INT,
    model VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB
);

CREATE INDEX IF NOT EXISTS idx_summaries_document ON summaries(document_id);
CREATE INDEX IF NOT EXISTS idx_summaries_type ON summaries(summary_type);

-- =====================================================================
-- Migration 007: Fix Conversations Schema
-- =====================================================================

-- Add missing columns if they don't exist
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='conversations' AND column_name='metadata') THEN
        ALTER TABLE conversations ADD COLUMN metadata JSONB;
    END IF;
END $$;

-- =====================================================================
-- VERIFICATION QUERIES
-- =====================================================================

-- Count tables created
SELECT COUNT(*) as total_tables 
FROM information_schema.tables 
WHERE table_schema = 'public' AND table_type = 'BASE TABLE';

-- List all tables
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
ORDER BY table_name;

-- Check pgvector extension
SELECT * FROM pg_extension WHERE extname = 'vector';

-- SUCCESS MESSAGE
SELECT 'All migrations completed successfully!' as status;
