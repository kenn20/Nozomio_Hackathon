-- CogWatch Database Schema
-- Run via: npx @insforge/cli db query --file cogwatch/schema.sql
-- Or execute each statement individually via npx @insforge/cli db query "..."

-- 1. Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Decision records table
CREATE TABLE IF NOT EXISTS decision_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source TEXT NOT NULL CHECK (source IN ('obsidian', 'github', 'claude_session')),
    content TEXT NOT NULL,
    context TEXT NOT NULL DEFAULT '',
    timestamp TIMESTAMPTZ NOT NULL DEFAULT now(),
    embedding vector(1536),
    tags TEXT[] DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'superseded', 'stale')),
    created_at TIMESTAMPTZ DEFAULT now()
);

-- 3. Personas table
CREATE TABLE IF NOT EXISTS personas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    system_prompt TEXT NOT NULL,
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- 4. Alerts table
CREATE TABLE IF NOT EXISTS alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    old_decision_id UUID REFERENCES decision_records(id),
    new_decision_id UUID REFERENCES decision_records(id),
    contradiction_type TEXT NOT NULL CHECK (contradiction_type IN ('direct_contradiction', 'forgotten_resolution', 'stale_thread')),
    severity TEXT NOT NULL CHECK (severity IN ('low', 'medium', 'high')),
    explanation TEXT NOT NULL,
    persona_responses JSONB DEFAULT '[]',
    acknowledged BOOLEAN DEFAULT false,
    resolution TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- 5. Settings table
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value JSONB NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- 6. HNSW index for fast similarity search
CREATE INDEX IF NOT EXISTS idx_decision_records_embedding
    ON decision_records USING hnsw (embedding vector_cosine_ops);

-- 7. Index for filtering by source and status
CREATE INDEX IF NOT EXISTS idx_decision_records_source ON decision_records(source);
CREATE INDEX IF NOT EXISTS idx_decision_records_status ON decision_records(status);
CREATE INDEX IF NOT EXISTS idx_alerts_acknowledged ON alerts(acknowledged);
CREATE INDEX IF NOT EXISTS idx_alerts_created_at ON alerts(created_at DESC);

-- 8. Similarity search function
CREATE OR REPLACE FUNCTION match_decisions(
    query_embedding vector(1536),
    match_count INT DEFAULT 5,
    match_threshold FLOAT DEFAULT 0.75
) RETURNS TABLE (
    id UUID,
    source TEXT,
    content TEXT,
    context TEXT,
    timestamp TIMESTAMPTZ,
    tags TEXT[],
    status TEXT,
    similarity FLOAT
)
LANGUAGE sql STABLE AS $$
    SELECT
        id, source, content, context, timestamp, tags, status,
        1 - (embedding <=> query_embedding) AS similarity
    FROM decision_records
    WHERE embedding IS NOT NULL
      AND 1 - (embedding <=> query_embedding) > match_threshold
    ORDER BY embedding <=> query_embedding
    LIMIT match_count;
$$;

-- 9. Seed default personas
INSERT INTO personas (name, system_prompt, active) VALUES
('Elon Musk',
 'You think from first principles. You challenge assumptions ruthlessly. You believe most processes exist because of inertia, not logic. When you see a contradiction, you ask: ''What is the physics of this problem?'' You favor speed, iteration, and deleting unnecessary complexity. You are direct to the point of being blunt. Reference the user''s specific history when advising.',
 true),
('Jensen Huang',
 'You think about accelerated computing and parallel execution. You believe in betting big on platform shifts and riding exponential curves. When you see a contradiction, you ask: ''Is this a sign of a platform shift they are not acknowledging, or just drift?'' You value long-term vision over short-term consistency. You are encouraging but intellectually honest. Reference the user''s specific history when advising.',
 true)
ON CONFLICT DO NOTHING;

-- 10. Seed default settings
INSERT INTO settings (key, value) VALUES
('detection_threshold', '0.75'),
('connected_sources', '{"obsidian": {"enabled": false, "vault_path": ""}, "github": {"enabled": false, "repos": []}, "claude": {"enabled": false, "paths": []}}')
ON CONFLICT DO NOTHING;
