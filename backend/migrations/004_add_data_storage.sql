-- Phase 4: Data Storage & History Schema
-- Adds tables for persisting imported data and tracking ingestion history

-- Drop existing tables if they exist (development only)
-- DROP TABLE IF EXISTS data_rows CASCADE;

-- data_rows: Individual imported data rows stored as JSONB
CREATE TABLE IF NOT EXISTS data_rows (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    data_table_id UUID NOT NULL REFERENCES data_tables(id) ON DELETE CASCADE,
    row_index INTEGER NOT NULL,
    row_data JSONB NOT NULL,  -- Flexible JSON storage: {col1: val1, col2: val2, ...}
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT data_rows_table_index_unique UNIQUE (data_table_id, row_index)
);

-- Update data_files table with metadata columns
ALTER TABLE data_files
ADD COLUMN IF NOT EXISTS tables_found INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS tables_valid INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS tables_stored INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS rows_stored INTEGER DEFAULT 0;

-- Indexes for performance

-- Query rows by table
CREATE INDEX IF NOT EXISTS idx_data_rows_table_id ON data_rows(data_table_id);

-- Query rows by insertion time
CREATE INDEX IF NOT EXISTS idx_data_rows_created_at ON data_rows(created_at);

-- Search within JSON data (JSONB gin index for operators)
CREATE INDEX IF NOT EXISTS idx_data_rows_data_gin ON data_rows USING GIN (row_data);

-- Query data_files by status
CREATE INDEX IF NOT EXISTS idx_data_files_status_user ON data_files(status, user_id);

-- Query ingestion_runs by user
CREATE INDEX IF NOT EXISTS idx_ingestion_runs_user_created ON ingestion_runs(user_id, created_at DESC);

-- Comments
COMMENT ON TABLE data_rows IS 'Individual rows from imported data tables, stored as flexible JSONB';
COMMENT ON COLUMN data_rows.row_data IS 'Complete row data as JSON object';
COMMENT ON COLUMN data_rows.row_index IS 'Original row position in source file';

COMMENT ON COLUMN data_files.tables_found IS 'Number of tables detected in file';
COMMENT ON COLUMN data_files.tables_stored IS 'Number of tables successfully persisted';
COMMENT ON COLUMN data_files.rows_stored IS 'Total number of rows from all tables';

-- Views for common queries

-- View: User ingestion summary
DROP VIEW IF EXISTS v_user_ingestion_summary CASCADE;
CREATE VIEW v_user_ingestion_summary AS
SELECT
    ir.id,
    ir.user_id,
    df.file_name,
    ir.status,
    COUNT(DISTINCT dt.id) as tables_count,
    SUM(ir.records_stored) as total_rows,
    ir.created_at,
    ir.completed_at,
    CASE
        WHEN ir.status = 'completed' THEN ROUND(EXTRACT(EPOCH FROM (ir.completed_at - ir.started_at)))
        ELSE NULL
    END as duration_seconds
FROM ingestion_runs ir
LEFT JOIN data_files df ON ir.data_file_id = df.id
LEFT JOIN data_tables dt ON df.id = dt.data_file_id
GROUP BY ir.id, ir.user_id, df.file_name, ir.status, ir.created_at, ir.completed_at, ir.started_at;

-- View: Data quality summary
DROP VIEW IF EXISTS v_data_quality CASCADE;
CREATE VIEW v_data_quality AS
SELECT
    dt.id,
    dt.table_name,
    COUNT(dr.id) as row_count,
    dt.col_count,
    COUNT(DISTINCT dr.row_data) as distinct_rows,
    ROUND(100.0 * COUNT(DISTINCT dr.row_data) / COUNT(dr.id), 2) as uniqueness_pct,
    MIN(dr.created_at) as first_imported,
    MAX(dr.created_at) as last_imported
FROM data_tables dt
LEFT JOIN data_rows dr ON dt.id = dr.data_table_id
GROUP BY dt.id, dt.table_name, dt.col_count;

-- Functions for common operations

-- Function: Count rows in data table
DROP FUNCTION IF EXISTS count_table_rows(UUID) CASCADE;
CREATE FUNCTION count_table_rows(table_id UUID)
RETURNS INTEGER AS $$
    SELECT COUNT(*) FROM data_rows WHERE data_table_id = table_id;
$$ LANGUAGE SQL;

-- Function: Find duplicate rows
DROP FUNCTION IF EXISTS find_duplicate_rows(UUID) CASCADE;
CREATE FUNCTION find_duplicate_rows(table_id UUID)
RETURNS TABLE(row_data JSONB, count BIGINT) AS $$
    SELECT row_data, COUNT(*) as count
    FROM data_rows
    WHERE data_table_id = table_id
    GROUP BY row_data
    HAVING COUNT(*) > 1
    ORDER BY count DESC;
$$ LANGUAGE SQL;

-- Triggers for data validation

-- Trigger: Update data_files row count on insert
DROP TRIGGER IF EXISTS trg_update_row_count ON data_rows CASCADE;
DROP FUNCTION IF EXISTS update_data_file_row_count() CASCADE;

CREATE FUNCTION update_data_file_row_count()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE data_files
    SET rows_stored = (
        SELECT SUM(COUNT(*))
        FROM data_rows
        JOIN data_tables ON data_rows.data_table_id = data_tables.id
        WHERE data_tables.data_file_id = data_files.id
        GROUP BY data_files.id
    )
    WHERE id IN (
        SELECT data_file_id FROM data_tables
        WHERE id = NEW.data_table_id
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_update_row_count
AFTER INSERT ON data_rows
FOR EACH ROW
EXECUTE FUNCTION update_data_file_row_count();

-- Grant permissions (if needed)
-- GRANT SELECT ON data_rows TO web_app;
-- GRANT INSERT ON data_rows TO web_app;
-- GRANT SELECT ON v_user_ingestion_summary TO web_app;
-- GRANT SELECT ON v_data_quality TO web_app;

-- Verify views and functions
-- SELECT * FROM v_user_ingestion_summary WHERE user_id = 1;
-- SELECT * FROM v_data_quality WHERE table_name LIKE '%Survey%';
-- SELECT * FROM find_duplicate_rows(101);
