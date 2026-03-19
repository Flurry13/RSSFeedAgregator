-- RSSFeed2 Clean-Slate Schema
-- Drops all old tables and creates new simplified schema

-- Drop old schema (order matters for foreign keys)
DROP VIEW IF EXISTS v_topic_statistics CASCADE;
DROP VIEW IF EXISTS v_recent_headlines CASCADE;
DROP TABLE IF EXISTS event_group_members CASCADE;
DROP TABLE IF EXISTS event_groups CASCADE;
DROP TABLE IF EXISTS events CASCADE;
DROP TABLE IF EXISTS topic_classifications CASCADE;
DROP TABLE IF EXISTS embeddings CASCADE;
DROP TABLE IF EXISTS processing_jobs CASCADE;
DROP TABLE IF EXISTS metrics CASCADE;
DROP TABLE IF EXISTS headlines CASCADE;
DROP TABLE IF EXISTS feeds CASCADE;

-- Drop old enum types
DROP TYPE IF EXISTS processing_status CASCADE;
DROP TYPE IF EXISTS event_type CASCADE;
DROP TYPE IF EXISTS news_category CASCADE;

-- Drop old extensions we no longer need
DROP EXTENSION IF EXISTS "uuid-ossp";
DROP EXTENSION IF EXISTS "btree_gin";

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Drop old trigger function if exists
DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE;

-- Sources table (replaces feeds.json and old feeds table)
CREATE TABLE sources (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    url TEXT UNIQUE NOT NULL,
    language TEXT NOT NULL DEFAULT 'en',
    country TEXT,
    group_name TEXT,
    category TEXT,
    subcategory TEXT,
    active BOOLEAN DEFAULT TRUE,
    last_fetched_at TIMESTAMPTZ,
    fetch_error TEXT,
    error_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_sources_active ON sources(active);
CREATE INDEX idx_sources_language ON sources(language);
CREATE INDEX idx_sources_category ON sources(category);

-- Headlines table (simplified)
CREATE TABLE headlines (
    id SERIAL PRIMARY KEY,
    source_id INTEGER NOT NULL REFERENCES sources(id),
    title TEXT NOT NULL,
    description TEXT,
    url TEXT NOT NULL,
    published_at TIMESTAMPTZ,
    language TEXT,
    translated_title TEXT,
    topic TEXT,
    topic_confidence FLOAT,
    entities JSONB,
    event_type TEXT,
    embedding_id TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(url, source_id)
);

CREATE INDEX idx_headlines_source_id ON headlines(source_id);
CREATE INDEX idx_headlines_published_at ON headlines(published_at);
CREATE INDEX idx_headlines_language ON headlines(language);
CREATE INDEX idx_headlines_topic ON headlines(topic);
CREATE INDEX idx_headlines_title_fts ON headlines USING gin(to_tsvector('simple', title));

-- Event clusters table
CREATE TABLE event_clusters (
    id SERIAL PRIMARY KEY,
    label TEXT NOT NULL,
    event_type TEXT,
    key_entities JSONB,
    summary TEXT,
    start_time TIMESTAMPTZ,
    end_time TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_event_clusters_start_time ON event_clusters(start_time);

-- Event cluster members (junction)
CREATE TABLE event_cluster_members (
    cluster_id INTEGER REFERENCES event_clusters(id) ON DELETE CASCADE,
    headline_id INTEGER REFERENCES headlines(id) ON DELETE CASCADE,
    similarity_score FLOAT,
    PRIMARY KEY(cluster_id, headline_id)
);

CREATE INDEX idx_ecm_headline_id ON event_cluster_members(headline_id);

-- Views
CREATE VIEW v_recent_headlines AS
SELECT
    h.id, h.title, h.description, h.url, h.published_at,
    h.translated_title, h.topic, h.topic_confidence, h.language,
    s.name as source_name, s.country, s.group_name
FROM headlines h
JOIN sources s ON h.source_id = s.id
WHERE h.published_at > NOW() - INTERVAL '24 hours'
ORDER BY h.published_at DESC;

CREATE VIEW v_topic_stats AS
SELECT
    topic,
    COUNT(*) as headline_count,
    AVG(topic_confidence) as avg_confidence,
    MAX(published_at) as latest_headline
FROM headlines
WHERE topic IS NOT NULL
  AND published_at > NOW() - INTERVAL '7 days'
GROUP BY topic
ORDER BY headline_count DESC;

-- Trigger for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_headlines_updated_at BEFORE UPDATE ON headlines
    FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();
CREATE TRIGGER update_sources_updated_at BEFORE UPDATE ON sources
    FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();
CREATE TRIGGER update_event_clusters_updated_at BEFORE UPDATE ON event_clusters
    FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();
