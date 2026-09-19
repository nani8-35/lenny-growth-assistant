CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE IF NOT EXISTS sessions (
 id UUID PRIMARY KEY, title TEXT NOT NULL, user_metadata JSONB NOT NULL DEFAULT '{}',
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS messages (
 id UUID PRIMARY KEY, session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
 role TEXT NOT NULL CHECK(role IN ('user','assistant')), content TEXT NOT NULL,
 sources JSONB NOT NULL DEFAULT '[]', provider TEXT, mode TEXT NOT NULL DEFAULT 'answer',
 status TEXT NOT NULL DEFAULT 'complete', created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS messages_session ON messages(session_id,created_at);
CREATE TABLE IF NOT EXISTS artifacts (
 id UUID PRIMARY KEY, message_id UUID NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
 artifact_type TEXT NOT NULL CHECK(artifact_type IN ('markdown','html')),
 title TEXT NOT NULL, content TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS episodes (
 id TEXT PRIMARY KEY, title TEXT NOT NULL, guest TEXT NOT NULL, published TEXT,
 source_url TEXT NOT NULL, checksum TEXT NOT NULL, embedding_model TEXT NOT NULL,
 indexed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS chunks (
 id BIGSERIAL PRIMARY KEY, episode_id TEXT NOT NULL REFERENCES episodes(id) ON DELETE CASCADE,
 ordinal INTEGER NOT NULL, content TEXT NOT NULL, timestamp_ref TEXT,
 embedding vector(768) NOT NULL, UNIQUE(episode_id,ordinal)
);
CREATE INDEX IF NOT EXISTS chunks_embedding ON chunks USING hnsw (embedding vector_cosine_ops);
