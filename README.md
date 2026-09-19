# The Lenny Growth Assistant

A local research workspace that turns Lenny’s Podcast transcripts into cited answers, essays, and rendered documents. FastAPI owns the API and persistence; the actual Pi Coding Agent SDK runs the restricted agent; PostgreSQL/pgvector stores conversations and retrieves evidence; React provides streaming chat and a side-by-side artifact viewer.

## Quick start — Apple Silicon

Prerequisites: Docker Desktop running, Ollama installed, 16 GB RAM recommended, roughly 8 GB available for models/images/data. First-time downloads need internet. Native Ollama uses Metal on Mac; Dockerized Ollama on macOS uses CPU.

```sh
cp .env.example .env
ollama serve                           # leave running, or use Ollama app
ollama pull llama3.1:8b
ollama create lenny-growth:8b -f Modelfile
ollama pull nomic-embed-text
# In another terminal, from this directory:
docker compose up --build -d
# Fetch the archive with its exact commit recorded in data/transcripts/manifest.json:
docker compose exec backend python -m scripts.download_transcripts --output /data/transcripts
# Start with a focused, real corpus for a fast demo:
docker compose exec backend python -m scripts.ingest --path /data/transcripts --guests rahul-vohra,elena-verna,brian-balfour,april-dunford
# Index everything when ready (may take several minutes):
docker compose exec backend python -m scripts.ingest --path /data/transcripts
```

Open **http://localhost:3000**. API docs: http://localhost:8000/docs. Repeated startup is `docker compose up -d`; volumes preserve conversations. `docker compose down` stops services without deleting data. Do not use `down -v` unless you intend to erase your database.

The Desktop delivery includes **Start Lenny.command**, a double-click launcher, and **Open Lenny.command**. The UI is a desktop-friendly web application, not an Electron executable. The launcher can use the bundled local Ollama runtime on this Mac; the repository remains portable via the setup above.

### CPU-only / Linux alternative

```sh
OLLAMA_MODEL=llama3.1:8b DOCKER_OLLAMA_BASE_URL=http://ollama:11434 docker compose --profile cpu up --build -d
 docker compose exec ollama ollama pull llama3.1:8b
 docker compose exec ollama ollama pull nomic-embed-text
```

Then run the same download/ingest commands. Keep both `OLLAMA_MODEL=llama3.1:8b` and `DOCKER_OLLAMA_BASE_URL=http://ollama:11434` in `.env` for future starts. CPU latency is materially higher.

## Model configuration

| Variable | Default / purpose |
|---|---|
| `DEFAULT_LLM_PROVIDER` | `ollama`; UI can select per request |
| `OLLAMA_MODEL` | `lenny-growth:8b`; local model profile with a 16k response context. It is built from the included `Modelfile`. |
| `OLLAMA_BASE_URL` | Native backend local endpoint |
| `DOCKER_OLLAMA_BASE_URL` | Compose uses `http://host.docker.internal:11434` by default |
| `EMBEDDING_MODEL` | `nomic-embed-text`, fixed 768 dimensions; changing model requires reindex |
| `ANTHROPIC_API_KEY` | Optional, required only for cloud requests |
| `ANTHROPIC_MODEL` | `claude-sonnet-4-5`, overridable without code changes |
| `RETRIEVAL_THRESHOLD` | `0.45`, cosine threshold; tune against evaluation set |
| `MODEL_TIMEOUT` | `240` seconds overall generation budget |
| `POSTGRES_*` | Local-only development database defaults |
| `DATABASE_URL`, `AGENT_URL` | Native development connections; Compose uses internal service names |
| `CORS_ORIGIN` | `http://localhost:3000` |

Put the cloud key only in local `.env`, then `docker compose up -d --force-recreate agent`. Choose **Claude · Cloud** in the UI. Cloud mode sends the question, recent conversation, and retrieved excerpts to Anthropic. There is **no silent fallback** in either direction. Missing keys produce an actionable error. A paid API key is separate from a consumer Claude subscription.

## Product walkthrough

1. Ask “How should an early-stage team measure product-market fit?”
2. Expand source cards and inspect the exact excerpt and original episode.
3. Follow up: “How would I apply that to a small B2B SaaS team?”
4. Choose **Write an essay** and request a 1,250-word piece. Check the word count and citations.
5. Choose **Document** or **HTML** to create an artifact from the discussion; inspect Preview/Source and download.
6. Start a second conversation and return to the first; context and artifacts are stored independently.
7. Ask an unsupported question such as today's weather; the assistant should acknowledge the gap.

## Structure and design decisions

- `backend/app`: validation, health, PostgreSQL schema, retrieval, SSE and transactional persistence.
- `backend/scripts`: traceable archive download and idempotent per-episode ingestion.
- `agent/src`: Pi Coding Agent service, model routing and versioned skill prompts. Built-in shell/filesystem tools and resource discovery are disabled.
- `agent/skills/ship30.md`: source-derived, reusable writing rubric. Adapts the publisher’s short atomic essay principles to the assignment’s longer word count.
- `frontend/src`: accessible responsive workspace, source cards and isolated artifacts.
- `docs`: PRD, architecture, design, evaluation, security, and demo handoff.
- `agent_transcripts`: sanitized build record, including failed attempts and corrections.

Pinned Pi SDK 0.73.1 uses its published `@mariozechner` package name. Upstream subsequently renamed packages; do not mix the latest renamed SDK examples with this version's API. The integration uses the installed SDK's `AuthStorage`, `ModelRegistry`, `createAgentSession`, and in-memory sessions.

## Retrieval and refresh

The downloader fetches [ChatPRD's public archive](https://github.com/ChatPRD/lennys-podcast-transcripts) at a resolved commit, records the archive SHA-256, and extracts only episode Markdown. Transcripts are educational source material owned by their creators; they are downloaded into ignored `data/`, not committed.

Ingestion parses YAML metadata, tracks timestamps, splits near paragraph/speaker boundaries (~600 estimated tokens, ~100 overlap), embeds locally, and writes to a cosine HNSW index. Source hashes skip unchanged episodes. `--force` re-embeds selected episodes. Download and rerun ingestion to refresh. Removed upstream episodes are deliberately retained until an operator reviews removal. A failed embedding leaves the old episode intact because replacement is transactional.

Question retrieval uses the same embedding model, a relevance floor, and at most two passages per episode. Short referential follow-ups include recent user questions. A weak/empty result bypasses generation with an explicit abstention. Inline citation IDs are checked against the retrieved source set. This verifies reference identity, **not** whether each claim logically follows from its citation; use the manual evaluation rubric.

## Tests

```sh
# Backend, including real PostgreSQL integration against a separate test DB:
docker compose exec db createdb -U lenny lenny_test
docker compose exec -e TEST_DATABASE_URL=postgresql://lenny:lenny-local-only@db:5432/lenny_test backend python -m pytest -q
# Node 22+ and pnpm 11 for frontend / agent tests:
cd frontend && pnpm install --frozen-lockfile && pnpm test && pnpm run build
cd ../agent && pnpm install --frozen-lockfile && pnpm test
```

Without `TEST_DATABASE_URL`, the database integration test is explicitly skipped. It must not be reported as passed. It creates uniquely identified fixtures and removes only those fixtures. See `docs/verification.md` for actual results and `docs/evaluation.md` for the claim-level evaluation plan.

## Troubleshooting

- **Database unavailable:** `docker compose ps`, `docker compose logs db backend`. Check volume permissions and credentials. API health reports degradation rather than returning fake data.
- **No passages:** Run ingestion, then inspect `/api/health`; no model answer is generated from an empty index.
- **Ollama unavailable:** `curl http://localhost:11434/api/tags`; confirm both models exist. On Mac use native Ollama. Test host connectivity from the backend container.
- **Cloud unavailable:** Set a valid API key, check quota/model access, recreate the agent container. No key values are logged.
- **Generation timeout:** Pick a smaller model or increase `MODEL_TIMEOUT`. Failed/canceled generations are visibly incomplete and excluded from later model history.
- **Port occupied:** Stop another copy of the app before Compose startup. Native development and Compose use the same frontend/API ports.
- **Blank artifact:** Use Source to inspect the model output. HTML intentionally blocks scripts, remote assets, forms, and navigation. CSS is permitted only in the isolated preview.
- **Logs:** `docker compose logs --tail=100 backend agent`. JSON records contain request IDs, retrieval count, first-token latency, and error class; never full prompts or keys.

## Operational limits and handoff

This is a single-user local deployment, bound to localhost. UUID sessions and metadata are not authentication. Add authentication, ownership checks, TLS, quotas, migrations, backup/restore, and a retention policy before public hosting. Do not expose the internal agent port. PostgreSQL volume backups must be tested before upgrades. The schema initializer is idempotent for first deployment; future schema changes need versioned migrations.

The public repository is https://github.com/nani8-35/lenny-growth-assistant. A cloud live test requires an Anthropic account with API credit, and the camera-on YouTube demo requires owner participation. See `docs/submission-checklist.md`; no unperformed test or upload is represented as complete.
