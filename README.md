# The Lenny Growth Assistant

A research workspace for turning Lenny’s Podcast transcripts into cited answers, Ship 30 essays, Markdown, and safe HTML artifacts. FastAPI owns validation, retrieval, persistence, and streaming; a restricted Pi Coding Agent service owns model execution; PostgreSQL/pgvector stores the archive and conversation records; React provides the desktop-first interface.

**Temporary evaluator deployment:** [lenny-growth-assistant-iau1.onrender.com](https://lenny-growth-assistant-iau1.onrender.com). It uses Render’s free tier and may need about a minute to wake after inactivity. The public service is for evaluation only; do not enter personal or sensitive information.

## Run locally (required Ollama demonstration)

Prerequisites: Docker Desktop, Ollama, 16 GB RAM recommended, and about 8 GB available. Native Ollama uses Metal on Apple Silicon.

```sh
cp .env.example .env
ollama serve
ollama pull llama3.1:8b
ollama create lenny-growth:8b -f Modelfile
ollama pull nomic-embed-text
docker compose up --build -d
docker compose exec backend python -m scripts.download_transcripts --output /data/transcripts
docker compose exec backend python -m scripts.ingest --path /data/transcripts --guests rahul-vohra,elena-verna,brian-balfour,april-dunford
```

Open [http://localhost:3000](http://localhost:3000). Repeated starts use `docker compose up -d`; volumes preserve data. Use `docker compose down` to stop services without deleting the database. The desktop delivery includes `Start Lenny.command` and `Open Lenny.command`.

For CPU-only Linux, use `OLLAMA_MODEL=llama3.1:8b DOCKER_OLLAMA_BASE_URL=http://ollama:11434 docker compose --profile cpu up --build -d`, then pull both models inside the Ollama container.

## Providers and safe failure behavior

| Provider | Use | Failure behavior |
|---|---|---|
| **Ollama · Local** | Required local demonstration; transcript embeddings and local generation | Reports unavailable model or timeout; never sends a local request to cloud automatically. |
| **Gemini · Cloud** | Temporary Render deployment default | Sends the question, recent conversation, and retrieved excerpts only after the user selects/uses Gemini. A missing, rejected, or 15-second timed-out response returns a clearly labeled, cited archive-excerpt fallback. |
| **Claude · Cloud** | Optional local provider | Requires `ANTHROPIC_API_KEY`; reports a configuration error with no automatic fallback. |

Set secrets only in ignored `.env` locally or Render’s secret environment variables. Never commit them. The cloud path uses Gemini’s OpenAI-compatible generation endpoint; it does **not** use Crawl API or Gemini Search Grounding. Grounding comes from the retrieved transcript excerpts in PostgreSQL. This tradeoff avoids a second paid search/crawl dependency and is documented in [docs/architecture.md](docs/architecture.md).

Key settings are `DEFAULT_LLM_PROVIDER`, `GEMINI_API_KEY`, `GEMINI_MODEL`, `ANTHROPIC_API_KEY`, `OLLAMA_MODEL`, `EMBEDDING_MODEL`, `RETRIEVAL_MODE`, `MODEL_TIMEOUT`, and `CORS_ORIGIN`. See `.env.example` for safe local defaults.

## Product walkthrough

1. Ask how an early-stage team should measure product-market fit.
2. Inspect source cards, exact excerpts, timestamps, and original episode links.
3. Ask a referential follow-up about a B2B SaaS team.
4. Choose **Write an essay** for a 1,250-word Ship 30 draft and check citations.
5. Choose **Document** or **HTML**; inspect its isolated Preview/Source and download it.
6. Create another conversation and return to the first. Browser-local workspace ownership keeps separate visitors’ newly created conversations apart.
7. Ask for current weather to see a retrieval abstention rather than invented evidence.

## Design and project structure

- `backend/app`: FastAPI validation, SSE, workspace ownership, health, PostgreSQL schema, retrieval, and transactional persistence.
- `backend/scripts`: traceable archive download and idempotent ingestion.
- `agent/src`: restricted Pi Coding Agent model router; no shell, filesystem, browser, extensions, or agent tools.
- `agent/skills/ship30.md`: reusable, source-derived Ship 30 writing rubric.
- `frontend/src`: desktop-first React workspace, source cards, and isolated artifact viewer.
- `deploy/`, `Dockerfile.render`: single-service Render image that runs the internal agent and FastAPI.
- `docs/`: PRD, architecture, security, evaluation, verification, deployment notes, and camera-on demo script.

Local retrieval uses a 768-dimensional `nomic-embed-text` embedding and HNSW cosine index. The Render service uses deterministic PostgreSQL full-text retrieval (`RETRIEVAL_MODE=lexical`) because it avoids an Ollama embedding sidecar; its seeded archive stays available. Both modes return exact excerpts, bounded source IDs, and source URLs. Citation checks validate source identifiers; a human must still assess whether a claim follows from its citation.

## Validation

```sh
# PostgreSQL integration tests use a separate database
 docker compose exec db createdb -U lenny lenny_test
 docker compose exec -e TEST_DATABASE_URL=postgresql://lenny:lenny-local-only@db:5432/lenny_test backend python -m pytest -q
# Node 22+ and pnpm 11
cd frontend && pnpm install --frozen-lockfile && pnpm test && pnpm run build
cd ../agent && pnpm install --frozen-lockfile && pnpm test
```

See [docs/verification.md](docs/verification.md) for recorded evidence and [docs/evaluation.md](docs/evaluation.md) for the manual claim-level rubric.

## Public deployment boundaries

Each browser receives an unguessable workspace token stored in `localStorage`; FastAPI requires it for session, chat, and artifact access. This prevents ordinary cross-visitor access to newly created conversations, but it is not a full account system: a user who exposes their browser token exposes their workspace, and deleting browser storage loses access to that workspace. Legacy rows without an owner token are not exposed through the public UI.

The Render free service has no durability, uptime, backup, rate-limit, or identity guarantee suitable for production. Before genuine public use, add real authentication, server-side rate limits, TLS/domain controls, migrations, backups, retention/deletion controls, and monitoring alerts. See [docs/security.md](docs/security.md) and [docs/deployment.md](docs/deployment.md).

The local 8B model did not meet the aspirational under-four-second first-token target in the recorded verification run; the demo should state the measured result honestly. The supplied [camera-on script](docs/demo-script.md) explicitly shows the local Ollama path and the cloud fallback behavior.

Repository: [nani8-35/lenny-growth-assistant](https://github.com/nani8-35/lenny-growth-assistant). The video and final submission links remain user-uploaded deliverables; do not mark them complete until their URLs are verified.
