-- Migration 006: Add Summaries and Claim Cards
-- Phase 6 - Summaries + claim cards (offline)
-- Dependencies: 001_init_phase1.sql (corpus), 005_add_insights.sql

-- Topic briefs table: precomputed summary bullets for each topic
CREATE TABLE IF NOT EXISTS topic_briefs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    corpus_id UUID NOT NULL REFERENCES corpora(id) ON DELETE CASCADE,
    topic VARCHAR(255) NOT NULL,
    bullets JSONB NOT NULL DEFAULT '[]'::jsonb, -- array of bullet strings
    key_numbers JSONB NOT NULL DEFAULT '[]'::jsonb, -- array of {value, label, unit, citation}
    linked_node_ids JSONB DEFAULT '[]'::jsonb, -- array of node UUIDs for evidence
    linked_series_ids JSONB DEFAULT '[]'::jsonb, -- array of indicator_series UUIDs
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Claim cards table: atomic claim + explanation + evidence
CREATE TABLE IF NOT EXISTS claim_cards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    corpus_id UUID NOT NULL REFERENCES corpora(id) ON DELETE CASCADE,
    topic VARCHAR(255) NOT NULL,
    claim_text TEXT NOT NULL,
    explanation TEXT, -- practitioner-tone explanation
    evidence_node_ids JSONB DEFAULT '[]'::jsonb, -- array of node UUIDs
    evidence_series_ids JSONB DEFAULT '[]'::jsonb, -- array of indicator_series UUIDs
    confidence DECIMAL(3,2) DEFAULT 1.0 CHECK (confidence >= 0 AND confidence <= 1),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_topic_briefs_corpus ON topic_briefs(corpus_id);
CREATE INDEX IF NOT EXISTS idx_topic_briefs_topic ON topic_briefs(topic);
CREATE INDEX IF NOT EXISTS idx_claim_cards_corpus ON claim_cards(corpus_id);
CREATE INDEX IF NOT EXISTS idx_claim_cards_topic ON claim_cards(topic);

-- GIN indexes for JSONB array searches
CREATE INDEX IF NOT EXISTS idx_topic_briefs_linked_nodes ON topic_briefs USING GIN(linked_node_ids);
CREATE INDEX IF NOT EXISTS idx_topic_briefs_linked_series ON topic_briefs USING GIN(linked_series_ids);
CREATE INDEX IF NOT EXISTS idx_claim_cards_evidence_nodes ON claim_cards USING GIN(evidence_node_ids);
CREATE INDEX IF NOT EXISTS idx_claim_cards_evidence_series ON claim_cards USING GIN(evidence_series_ids);

-- Function to get topic briefs for a corpus
CREATE OR REPLACE FUNCTION get_topic_briefs(p_corpus_id UUID)
RETURNS TABLE (
    id UUID,
    topic VARCHAR,
    bullets JSONB,
    key_numbers JSONB,
    linked_node_ids JSONB,
    linked_series_ids JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        tb.id,
        tb.topic,
        tb.bullets,
        tb.key_numbers,
        tb.linked_node_ids,
        tb.linked_series_ids
    FROM topic_briefs tb
    WHERE tb.corpus_id = p_corpus_id
    ORDER BY tb.topic;
END;
$$ LANGUAGE plpgsql STABLE;

-- Function to get claim cards by topic
CREATE OR REPLACE FUNCTION get_claim_cards_by_topic(p_corpus_id UUID, p_topic VARCHAR)
RETURNS TABLE (
    id UUID,
    claim_text TEXT,
    explanation TEXT,
    evidence_node_ids JSONB,
    evidence_series_ids JSONB,
    confidence DECIMAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        cc.id,
        cc.claim_text,
        cc.explanation,
        cc.evidence_node_ids,
        cc.evidence_series_ids,
        cc.confidence
    FROM claim_cards cc
    WHERE cc.corpus_id = p_corpus_id
      AND cc.topic = p_topic
    ORDER BY cc.confidence DESC, cc.created_at DESC;
END;
$$ LANGUAGE plpgsql STABLE;

-- Function to search claim cards by text
CREATE OR REPLACE FUNCTION search_claim_cards(p_corpus_id UUID, p_search_text TEXT)
RETURNS TABLE (
    id UUID,
    topic VARCHAR,
    claim_text TEXT,
    explanation TEXT,
    evidence_node_ids JSONB,
    evidence_series_ids JSONB,
    confidence DECIMAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        cc.id,
        cc.topic,
        cc.claim_text,
        cc.explanation,
        cc.evidence_node_ids,
        cc.evidence_series_ids,
        cc.confidence
    FROM claim_cards cc
    WHERE cc.corpus_id = p_corpus_id
      AND (
          cc.claim_text ILIKE '%' || p_search_text || '%' OR
          cc.explanation ILIKE '%' || p_search_text || '%' OR
          cc.topic ILIKE '%' || p_search_text || '%'
      )
    ORDER BY cc.confidence DESC, cc.created_at DESC
    LIMIT 50;
END;
$$ LANGUAGE plpgsql STABLE;

-- Function to count claim cards by topic
CREATE OR REPLACE FUNCTION count_claim_cards_by_topic(p_corpus_id UUID)
RETURNS TABLE (
    topic VARCHAR,
    card_count BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        cc.topic,
        COUNT(*) as card_count
    FROM claim_cards cc
    WHERE cc.corpus_id = p_corpus_id
    GROUP BY cc.topic
    ORDER BY card_count DESC;
END;
$$ LANGUAGE plpgsql STABLE;

-- Trigger to update updated_at on topic_briefs
CREATE OR REPLACE FUNCTION update_topic_briefs_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER topic_briefs_updated_at
    BEFORE UPDATE ON topic_briefs
    FOR EACH ROW
    EXECUTE FUNCTION update_topic_briefs_timestamp();

-- Trigger to update updated_at on claim_cards
CREATE OR REPLACE FUNCTION update_claim_cards_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER claim_cards_updated_at
    BEFORE UPDATE ON claim_cards
    FOR EACH ROW
    EXECUTE FUNCTION update_claim_cards_timestamp();

-- Comments for documentation
COMMENT ON TABLE topic_briefs IS 'Precomputed topic summaries with bullets and key numbers for each corpus';
COMMENT ON TABLE claim_cards IS 'Atomic claims with explanations and evidence citations, used for retrieval';
COMMENT ON COLUMN topic_briefs.bullets IS 'Array of bullet point strings (3-8 bullets per topic)';
COMMENT ON COLUMN topic_briefs.key_numbers IS 'Array of key statistics: [{value, label, unit, citation}]';
COMMENT ON COLUMN claim_cards.claim_text IS 'One-sentence atomic claim';
COMMENT ON COLUMN claim_cards.explanation IS 'Practitioner-tone explanation of the claim';
COMMENT ON COLUMN claim_cards.confidence IS 'Confidence score 0-1 for the claim';
