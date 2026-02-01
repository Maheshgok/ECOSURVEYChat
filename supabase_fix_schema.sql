-- SIMPLIFIED SCHEMA: Only what's needed for basic RAG chat
-- Run this in Supabase SQL Editor

-- Drop all tables
DROP TABLE IF EXISTS messages CASCADE;
DROP TABLE IF EXISTS chunks CASCADE;
DROP TABLE IF EXISTS documents CASCADE;
DROP TABLE IF EXISTS corpuses CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- Enable pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- 1. Users (Firebase auth)
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    google_id VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    picture VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_users_google_id ON users(google_id);

-- 2. Corpuses (document collections)
CREATE TABLE corpuses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Documents (PDFs, XLSX files)
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    corpus_id UUID NOT NULL REFERENCES corpuses(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    filename VARCHAR(255),
    year INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_documents_corpus_id ON documents(corpus_id);

-- 4. Chunks (text with embeddings for RAG)
CREATE TABLE chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    corpus_id UUID NOT NULL REFERENCES corpuses(id) ON DELETE CASCADE,
    text TEXT NOT NULL,
    page_start INT,
    page_end INT,
    chunk_index INT,
    embedding vector(3072),  -- OpenAI text-embedding-3-large
    meta JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_chunks_document_id ON chunks(document_id);
CREATE INDEX idx_chunks_corpus_id ON chunks(corpus_id);

-- 5. Messages (chat history)
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    corpus_id UUID NOT NULL REFERENCES corpuses(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    meta JSONB DEFAULT '{}',  -- Store citations, conversation_id, etc. here
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_messages_user_id ON messages(user_id);
CREATE INDEX idx_messages_corpus_id ON messages(corpus_id);

-- Insert default corpus
INSERT INTO corpuses (name, description) 
VALUES ('Economic Survey 2024-25', 'Economic Survey of India 2024-25');
