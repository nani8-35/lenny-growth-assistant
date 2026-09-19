# Architecture

Browser → frontend (React/Vite, Nginx) → FastAPI → PostgreSQL 16 + pgvector.
FastAPI → internal Pi Coding Agent Node service → Ollama on host or Anthropic.
FastAPI/ingestion → Ollama nomic-embed-text (768 dimensions).

## Boundaries
FastAPI owns validation, sessions, retrieval, structured SSE, and persistence. Pi's actual `createAgentSession` runs inference with explicitly empty execution tools, isolated in-memory agent sessions, and application-owned prompts. PostgreSQL supplies history to each request. A new ephemeral Pi session prevents cross-user leakage and duplicate disk persistence. Provider choice is an allowlisted request field with an environment default. No automatic cloud fallback.

## Data
sessions: UUID, title, JSONB user_metadata, created_at, updated_at.
messages: UUID, session FK, role, text, JSONB sources, provider, mode, status, created_at.
artifacts: UUID, message FK, type, title, content, created_at.
episodes: stable source path key, title, guest, published date, source URL, checksum, embedding model, indexed_at.
chunks: bigserial key, episode FK, ordinal, text, timestamp, vector(768); unique episode/ordinal; HNSW cosine index.
A transaction replaces an episode's chunks only after new embeddings are ready. Unchanged hashes skip work. Refresh upserts current files; deleted upstream files require explicit reindex policy, never silent destructive cleanup.

## Retrieval
Parse YAML frontmatter and timestamped Markdown. Split at paragraph/speaker boundaries, target 600 estimated tokens with 100 overlap, enforce a hard maximum. Embed with the same pinned model for documents and questions. Cosine top-k plus threshold, limited per-episode repetition. Recent user turns provide follow-up context. Return source IDs, exact excerpt, title, guest, timestamp, and original URL. Empty/weak results bypass the LLM with a fixed abstention. Citations are checked against retrieved IDs; this checks reference validity, not semantic entailment.

## API and SSE
POST /api/sessions {title?, user_metadata?}; GET /api/sessions; GET /api/sessions/{uuid}.
POST /api/chat {session_id, message, provider?: ollama|anthropic, mode: answer|essay|markdown|html}.
GET /api/health reports DB, vector count, agent, Ollama, cloud configuration.
GET /api/artifacts/{uuid} returns persisted artifact.
SSE JSON events: status, sources, token, artifact, warning, done; error is terminal. Tokens are JSON-encoded. Client handles chunk boundaries and cancellation. Concurrent generation in one session is rejected with a database advisory lock. Input length and output length are bounded. Errors include a request ID; logs never contain credentials or complete prompts.

## Security and deployment
Only frontend and backend localhost ports are exposed. Internal agent and database stay on the Compose network. No tool has filesystem, shell, or browser access. Transcript/user content is explicitly untrusted data. HTML preview uses DOMPurify, strips scripts/handlers/frames/forms/remote URLs, and iframe sandbox without allow-same-origin. CSP blocks every network channel and scripts. Markdown raw HTML is disabled. Downloads remain untrusted documents.

Docker Compose handles DB readiness and schema initialization. Native Ollama on Apple Silicon uses Metal; a CPU Ollama Compose profile supports other machines. Models and transcripts require initial network downloads. .env is ignored by Git. Health degradation is visible; startup does not pretend a missing index is ready.
