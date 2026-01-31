-- Phase 3: Data Ingestion Schema
-- Adds ingestion_runs table for tracking ingestion operations
-- NOTE: data_files, data_sheets, data_tables, data_columns already created in Phase 2
-- This migration only adds the ingestion_runs table and indexes

-- ingestion_runs: Track ingestion operations (uses UUID foreign keys)
CREATE TABLE IF NOT EXISTS ingestion_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    data_file_id UUID REFERENCES data_files(id) ON DELETE CASCADE,
    status VARCHAR(50) NOT NULL DEFAULT 'pending', -- pending, processing, completed, failed
    tables_parsed INTEGER,
    tables_valid INTEGER,
    tables_stored INTEGER,
    records_stored INTEGER,
    error_message TEXT,
    started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_ingestion_runs_user_id ON ingestion_runs(user_id);
CREATE INDEX IF NOT EXISTS idx_ingestion_runs_file_id ON ingestion_runs(data_file_id);
CREATE INDEX IF NOT EXISTS idx_ingestion_runs_status ON ingestion_runs(status);

-- Comments
COMMENT ON TABLE ingestion_runs IS 'Ingestion operation tracking';
