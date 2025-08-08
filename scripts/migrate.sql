-- News AI Database Schema
-- PostgreSQL Migration Script

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";

-- Create enums
CREATE TYPE processing_status AS ENUM ('pending', 'processing', 'completed', 'failed');
CREATE TYPE event_type AS ENUM ('political', 'economic', 'social', 'environmental', 'technological', 'other');
CREATE TYPE news_category AS ENUM ('politics', 'economy', 'technology', 'science', 'environment', 'entertainment', 'world', 'business', 'education', 'art');

-- RSS Feeds table
CREATE TABLE feeds (
    id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(500) NOT NULL,
    url TEXT NOT NULL UNIQUE,
    country VARCHAR(10),
    language VARCHAR(10) NOT NULL,
    category VARCHAR(50),
    leaning VARCHAR(50),
    weight DECIMAL(3,2) DEFAULT 1.0,
    enabled BOOLEAN DEFAULT true,
    fetch_interval INTEGER DEFAULT 300,
    last_fetched TIMESTAMP WITH TIME ZONE,
    last_error TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Headlines table
CREATE TABLE headlines (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    feed_id VARCHAR(255) REFERENCES feeds(id),
    title TEXT NOT NULL,
    description TEXT,
    content TEXT,
    url TEXT NOT NULL,
    author VARCHAR(500),
    published_at TIMESTAMP WITH TIME ZONE,
    language VARCHAR(10),
    translated_title TEXT,
    translated_description TEXT,
    classification_status processing_status DEFAULT 'pending',
    embedding_status processing_status DEFAULT 'pending',
    event_extraction_status processing_status DEFAULT 'pending',
    processing_errors JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(url, feed_id)
);

-- Topic Classifications table
CREATE TABLE topic_classifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    headline_id UUID REFERENCES headlines(id) ON DELETE CASCADE,
    topic news_category NOT NULL,
    confidence DECIMAL(5,4) NOT NULL,
    rank INTEGER NOT NULL,
    model_version VARCHAR(100),
    processing_time_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(headline_id, topic, rank)
);

-- Events table (extracted from headlines)
CREATE TABLE events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    headline_id UUID REFERENCES headlines(id) ON DELETE CASCADE,
    event_hash VARCHAR(64) UNIQUE, -- SHA-256 hash for deduplication
    subject TEXT,
    predicate TEXT,
    object_text TEXT,
    event_type event_type,
    confidence DECIMAL(5,4),
    location TEXT,
    timestamp_extracted TIMESTAMP WITH TIME ZONE,
    entities JSONB, -- Store NER entities
    processing_time_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Event Groups table (clustering results)
CREATE TABLE event_groups (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    group_hash VARCHAR(64) UNIQUE,
    representative_event_id UUID REFERENCES events(id),
    event_count INTEGER DEFAULT 0,
    cohesion_score DECIMAL(5,4),
    summary TEXT,
    keywords TEXT[],
    start_time TIMESTAMP WITH TIME ZONE,
    end_time TIMESTAMP WITH TIME ZONE,
    geographic_scope TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Event Group Memberships (many-to-many)
CREATE TABLE event_group_members (
    group_id UUID REFERENCES event_groups(id) ON DELETE CASCADE,
    event_id UUID REFERENCES events(id) ON DELETE CASCADE,
    added_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    PRIMARY KEY (group_id, event_id)
);

-- Vector Embeddings metadata (Qdrant sync)
CREATE TABLE embeddings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    headline_id UUID REFERENCES headlines(id) ON DELETE CASCADE,
    vector_id VARCHAR(255) UNIQUE, -- Qdrant point ID
    model_name VARCHAR(100) NOT NULL,
    dimension INTEGER NOT NULL,
    processing_time_ms INTEGER,
    synced_to_qdrant BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Processing Jobs queue
CREATE TABLE processing_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_type VARCHAR(50) NOT NULL, -- 'classify', 'translate', 'embed', 'extract', 'group'
    payload JSONB NOT NULL,
    status processing_status DEFAULT 'pending',
    priority INTEGER DEFAULT 5,
    max_retries INTEGER DEFAULT 3,
    retry_count INTEGER DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- System Metrics
CREATE TABLE metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    metric_name VARCHAR(100) NOT NULL,
    metric_value DECIMAL(15,6),
    tags JSONB,
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX idx_headlines_feed_id ON headlines(feed_id);
CREATE INDEX idx_headlines_published_at ON headlines(published_at);
CREATE INDEX idx_headlines_language ON headlines(language);
CREATE INDEX idx_headlines_classification_status ON headlines(classification_status);
CREATE INDEX idx_headlines_url_hash ON headlines USING hash(url);

CREATE INDEX idx_topic_classifications_headline_id ON topic_classifications(headline_id);
CREATE INDEX idx_topic_classifications_topic ON topic_classifications(topic);
CREATE INDEX idx_topic_classifications_confidence ON topic_classifications(confidence DESC);

CREATE INDEX idx_events_headline_id ON events(headline_id);
CREATE INDEX idx_events_event_hash ON events(event_hash);
CREATE INDEX idx_events_event_type ON events(event_type);
CREATE INDEX idx_events_timestamp ON events(timestamp_extracted);

CREATE INDEX idx_event_groups_representative_id ON event_groups(representative_event_id);
CREATE INDEX idx_event_groups_start_time ON event_groups(start_time);
CREATE INDEX idx_event_groups_cohesion ON event_groups(cohesion_score DESC);

CREATE INDEX idx_embeddings_headline_id ON embeddings(headline_id);
CREATE INDEX idx_embeddings_vector_id ON embeddings(vector_id);
CREATE INDEX idx_embeddings_synced ON embeddings(synced_to_qdrant);

CREATE INDEX idx_processing_jobs_status ON processing_jobs(status);
CREATE INDEX idx_processing_jobs_type ON processing_jobs(job_type);
CREATE INDEX idx_processing_jobs_priority ON processing_jobs(priority DESC);
CREATE INDEX idx_processing_jobs_created_at ON processing_jobs(created_at);

CREATE INDEX idx_metrics_name ON metrics(metric_name);
CREATE INDEX idx_metrics_recorded_at ON metrics(recorded_at);

-- Full-text search indexes
CREATE INDEX idx_headlines_title_fts ON headlines USING gin(to_tsvector('english', title));
CREATE INDEX idx_headlines_description_fts ON headlines USING gin(to_tsvector('english', description));

-- Trigger to update updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_headlines_updated_at BEFORE UPDATE ON headlines 
    FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();

CREATE TRIGGER update_feeds_updated_at BEFORE UPDATE ON feeds 
    FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();

CREATE TRIGGER update_event_groups_updated_at BEFORE UPDATE ON event_groups 
    FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();

-- Insert initial topic labels
INSERT INTO feeds (id, name, url, country, language, category, leaning, weight, enabled, fetch_interval) VALUES
('bbc_world', 'BBC World News', 'http://feeds.bbci.co.uk/news/world/rss.xml', 'UK', 'en', 'world', 'center', 1.0, true, 300),
('cnn_world', 'CNN World News', 'http://rss.cnn.com/rss/edition.rss', 'US', 'en', 'world', 'center-left', 1.0, true, 300),
('reuters_world', 'Reuters World News', 'https://feeds.reuters.com/reuters/worldNews', 'UK', 'en', 'world', 'center', 1.2, true, 180);

-- Create views for common queries
CREATE VIEW v_recent_headlines AS
SELECT 
    h.id,
    h.title,
    h.description,
    h.url,
    h.published_at,
    f.name as feed_name,
    f.country,
    f.language,
    tc.topic,
    tc.confidence
FROM headlines h
JOIN feeds f ON h.feed_id = f.id
LEFT JOIN topic_classifications tc ON h.id = tc.headline_id AND tc.rank = 1
WHERE h.published_at > NOW() - INTERVAL '24 hours'
ORDER BY h.published_at DESC;

CREATE VIEW v_topic_statistics AS
SELECT 
    tc.topic,
    COUNT(*) as headline_count,
    AVG(tc.confidence) as avg_confidence,
    MAX(h.published_at) as latest_headline
FROM topic_classifications tc
JOIN headlines h ON tc.headline_id = h.id
WHERE h.published_at > NOW() - INTERVAL '7 days'
GROUP BY tc.topic
ORDER BY headline_count DESC;

-- Grant permissions (adjust as needed)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO news_user;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO news_user; 