-- Phase 5: Insights, Summaries, and Embeddings
-- Adds tables for storing extracted insights and generated summaries

-- Create insights table
CREATE TABLE IF NOT EXISTS insights (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    data_table_id UUID NOT NULL REFERENCES data_tables(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    insight_type VARCHAR(50) NOT NULL,  -- 'statistic', 'pattern', 'anomaly', 'trend'
    metric VARCHAR(255) NOT NULL,        -- Column name being analyzed
    value TEXT,                          -- The actual insight value
    confidence DECIMAL(3,2),             -- 0-1 confidence score
    description TEXT,                    -- Human-readable description
    supporting_data JSONB,               -- Additional context {count, frequency, etc}
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create summaries table
CREATE TABLE IF NOT EXISTS summaries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    data_table_id UUID NOT NULL REFERENCES data_tables(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    summary_type VARCHAR(50) NOT NULL,   -- 'executive', 'detailed', 'statistical'
    content TEXT NOT NULL,               -- Markdown-formatted summary
    key_points TEXT[],                   -- Array of bullet point highlights
    metadata JSONB,                      -- Generation metadata {time, method, version}
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create insight embeddings table (for semantic search)
CREATE TABLE IF NOT EXISTS insight_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    insight_id UUID NOT NULL REFERENCES insights(id) ON DELETE CASCADE,
    embedding DECIMAL(5,4)[],            -- Array of floats for TF-IDF or VECTOR
    embedding_model VARCHAR(100),        -- 'tfidf', 'sentence-transformers', etc
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX idx_insights_table_user ON insights(data_table_id, user_id);
CREATE INDEX idx_insights_type ON insights(insight_type);
CREATE INDEX idx_insights_metric ON insights(metric);
CREATE INDEX idx_insights_created ON insights(created_at DESC);

CREATE INDEX idx_summaries_table_user ON summaries(data_table_id, user_id);
CREATE INDEX idx_summaries_type ON summaries(summary_type);
CREATE INDEX idx_summaries_created ON summaries(created_at DESC);

CREATE INDEX idx_embeddings_insight ON insight_embeddings(insight_id);

-- Create view for user insights summary
CREATE OR REPLACE VIEW v_user_insights_summary AS
SELECT 
    u.id as user_id,
    u.name as user_name,
    COUNT(DISTINCT i.data_table_id) as tables_analyzed,
    COUNT(i.id) as total_insights,
    COUNT(DISTINCT i.insight_type) as insight_types,
    MAX(i.created_at) as last_insight_date,
    COUNT(DISTINCT s.id) as summaries_generated
FROM users u
LEFT JOIN insights i ON u.id = i.user_id
LEFT JOIN summaries s ON u.id = s.user_id
GROUP BY u.id, u.name;

-- Create view for insight distribution
CREATE OR REPLACE VIEW v_insight_distribution AS
SELECT 
    insight_type,
    COUNT(*) as count,
    COUNT(DISTINCT data_table_id) as tables_with_insight,
    AVG(confidence) as avg_confidence,
    MIN(created_at) as first_date,
    MAX(created_at) as last_date
FROM insights
GROUP BY insight_type;

-- Create view for table insights overview
CREATE OR REPLACE VIEW v_table_insights_overview AS
SELECT 
    dt.id,
    dt.table_name,
    COUNT(DISTINCT i.id) as total_insights,
    COUNT(DISTINCT CASE WHEN i.insight_type = 'statistic' THEN i.id END) as statistics,
    COUNT(DISTINCT CASE WHEN i.insight_type = 'pattern' THEN i.id END) as patterns,
    COUNT(DISTINCT CASE WHEN i.insight_type = 'anomaly' THEN i.id END) as anomalies,
    COUNT(DISTINCT CASE WHEN i.insight_type = 'trend' THEN i.id END) as trends,
    COUNT(DISTINCT s.id) as summaries,
    AVG(i.confidence) as avg_confidence,
    MAX(i.created_at) as last_analyzed
FROM data_tables dt
LEFT JOIN insights i ON dt.id = i.data_table_id
LEFT JOIN summaries s ON dt.id = s.data_table_id
GROUP BY dt.id, dt.table_name;

-- Create function to get top insights
CREATE OR REPLACE FUNCTION get_top_insights(
    p_table_id UUID,
    p_limit INTEGER DEFAULT 10,
    p_min_confidence DECIMAL DEFAULT 0.5
)
RETURNS TABLE (
    id UUID,
    insight_type VARCHAR,
    metric VARCHAR,
    value TEXT,
    confidence DECIMAL,
    description TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        i.id,
        i.insight_type,
        i.metric,
        i.value,
        i.confidence,
        i.description
    FROM insights i
    WHERE i.data_table_id = p_table_id
        AND i.confidence >= p_min_confidence
    ORDER BY i.confidence DESC, i.created_at DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- Create function to search similar insights
CREATE OR REPLACE FUNCTION search_similar_insights(
    p_metric VARCHAR,
    p_limit INTEGER DEFAULT 5
)
RETURNS TABLE (
    id UUID,
    metric VARCHAR,
    value TEXT,
    similarity DECIMAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        i.id,
        i.metric,
        i.value,
        CASE 
            WHEN i.metric = p_metric THEN 1.0
            WHEN i.metric LIKE p_metric || '%' THEN 0.8
            WHEN i.metric LIKE '%' || p_metric THEN 0.6
            ELSE 0.3
        END as similarity
    FROM insights i
    WHERE i.metric ILIKE '%' || p_metric || '%'
    ORDER BY similarity DESC, i.created_at DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to update summary updated_at
CREATE OR REPLACE FUNCTION update_summary_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_summary_timestamp
BEFORE UPDATE ON summaries
FOR EACH ROW
EXECUTE FUNCTION update_summary_timestamp();

-- Create trigger to update insight updated_at
CREATE OR REPLACE FUNCTION update_insight_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_insight_timestamp
BEFORE UPDATE ON insights
FOR EACH ROW
EXECUTE FUNCTION update_insight_timestamp();

-- Grant permissions (optional - comment out if app_user role doesn't exist)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON insights TO app_user;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON summaries TO app_user;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON insight_embeddings TO app_user;
-- GRANT SELECT ON v_user_insights_summary TO app_user;
-- GRANT SELECT ON v_insight_distribution TO app_user;
-- GRANT SELECT ON v_table_insights_overview TO app_user;
-- GRANT EXECUTE ON FUNCTION get_top_insights TO app_user;
-- GRANT EXECUTE ON FUNCTION search_similar_insights TO app_user;

-- Summary of changes:
-- - insights: Store extracted statistical, pattern, anomaly, trend insights
-- - summaries: Store generated summaries (executive, detailed, etc)
-- - insight_embeddings: Store vector representations for semantic search
-- - 6 new indexes for query performance
-- - 3 summary views for analytics and monitoring
-- - 2 utility functions for insight retrieval and search
-- - 2 update triggers for timestamp management
