CREATE OR REPLACE FUNCTION match_decisions(
    query_embedding vector(1536),
    match_count INT DEFAULT 5,
    match_threshold FLOAT DEFAULT 0.75
) RETURNS TABLE (
    id UUID,
    source TEXT,
    content TEXT,
    context TEXT,
    "timestamp" TIMESTAMPTZ,
    tags TEXT[],
    status TEXT,
    similarity FLOAT
)
LANGUAGE sql STABLE AS $$
    SELECT id, source, content, context, "timestamp", tags, status,
           1 - (embedding <=> query_embedding) AS similarity
    FROM decision_records
    WHERE embedding IS NOT NULL
      AND 1 - (embedding <=> query_embedding) > match_threshold
    ORDER BY embedding <=> query_embedding
    LIMIT match_count;
$$;
