-- Digital Pulse Database Schema
-- Run this in Supabase SQL Editor

-- Posts table: stores all scraped social/news data
CREATE TABLE IF NOT EXISTS posts (
    id BIGSERIAL PRIMARY KEY,
    post_id TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL DEFAULT '',
    timestamp TIMESTAMPTZ NOT NULL,
    source TEXT NOT NULL,
    likes INTEGER DEFAULT 0,
    shares INTEGER DEFAULT 0,
    comments INTEGER DEFAULT 0,
    region TEXT,
    engagement_total FLOAT DEFAULT 0.0,
    engagement_velocity FLOAT DEFAULT 0.0,
    time_decay FLOAT DEFAULT 1.0,
    virality_score FLOAT DEFAULT 0.0,
    engagement_score FLOAT DEFAULT 0.0,
    cluster_id INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Narrative clusters
CREATE TABLE IF NOT EXISTS narrative_clusters (
    cluster_id SERIAL PRIMARY KEY,
    topic_label TEXT NOT NULL,
    keywords TEXT[] DEFAULT '{}',
    post_count INTEGER DEFAULT 0,
    influence_score FLOAT DEFAULT 0.0,
    avg_virality FLOAT DEFAULT 0.0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Emerging signals / alerts
CREATE TABLE IF NOT EXISTS emerging_signals (
    id BIGSERIAL PRIMARY KEY,
    cluster_id INTEGER,
    topic TEXT NOT NULL,
    growth_rate FLOAT NOT NULL,
    current_engagement FLOAT DEFAULT 0.0,
    previous_engagement FLOAT DEFAULT 0.0,
    detected_at TIMESTAMPTZ DEFAULT NOW(),
    severity TEXT DEFAULT 'medium',
    signal_type TEXT DEFAULT 'volume_spike',
    acknowledged BOOLEAN DEFAULT FALSE
);

-- Forecast results
CREATE TABLE IF NOT EXISTS forecasts (
    id BIGSERIAL PRIMARY KEY,
    topic TEXT NOT NULL,
    trend_prediction TEXT NOT NULL,
    confidence_score FLOAT DEFAULT 0.0,
    predicted_engagement FLOAT DEFAULT 0.0,
    forecast_hours INTEGER DEFAULT 48,
    data_points JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Pulse score history
CREATE TABLE IF NOT EXISTS pulse_scores (
    id BIGSERIAL PRIMARY KEY,
    score FLOAT NOT NULL,
    breakdown JSONB DEFAULT '{}',
    top_narratives TEXT[] DEFAULT '{}',
    trend_direction TEXT DEFAULT 'stable',
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_posts_timestamp ON posts(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_posts_created_at ON posts(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_posts_source ON posts(source);
CREATE INDEX IF NOT EXISTS idx_posts_cluster ON posts(cluster_id);
CREATE INDEX IF NOT EXISTS idx_posts_virality ON posts(virality_score DESC);
CREATE INDEX IF NOT EXISTS idx_emerging_detected ON emerging_signals(detected_at DESC);
CREATE INDEX IF NOT EXISTS idx_posts_post_id ON posts(post_id);

-- Updated_at trigger
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER posts_updated_at
    BEFORE UPDATE ON posts
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

CREATE OR REPLACE TRIGGER clusters_updated_at
    BEFORE UPDATE ON narrative_clusters
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();
