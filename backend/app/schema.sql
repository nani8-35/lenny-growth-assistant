CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE IF NOT EXISTS users (
 id UUID PRIMARY KEY, email TEXT NOT NULL UNIQUE, name TEXT NOT NULL, password_hash TEXT NOT NULL,
 is_admin BOOLEAN NOT NULL DEFAULT FALSE, created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS auth_sessions (
 token_hash TEXT PRIMARY KEY, user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 expires_at TIMESTAMPTZ NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS auth_sessions_user ON auth_sessions(user_id);
CREATE TABLE IF NOT EXISTS sessions (
 id UUID PRIMARY KEY, title TEXT NOT NULL, user_metadata JSONB NOT NULL DEFAULT '{}',
 owner_token TEXT, user_id UUID REFERENCES users(id) ON DELETE CASCADE, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
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

ALTER TABLE sessions ADD COLUMN IF NOT EXISTS owner_token TEXT;
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES users(id) ON DELETE CASCADE;
CREATE INDEX IF NOT EXISTS sessions_owner_updated ON sessions(owner_token, updated_at DESC);
CREATE INDEX IF NOT EXISTS sessions_user_updated ON sessions(user_id, updated_at DESC);
