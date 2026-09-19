# Deployment and operability

## Local evaluator path

`docker compose up --build -d` starts PostgreSQL/pgvector, FastAPI, the internal Pi agent, and the React/Nginx frontend. Ollama runs natively on Apple Silicon for Metal acceleration or through the optional CPU profile. Health is available at `/api/health`; it reports database, archive counts, agent, provider, embedding readiness, and the selected default provider. JSON logs contain request IDs, retrieval counts, first-token latency, and error classes.

## Temporary Render path

Render builds `Dockerfile.render`. The final image builds the React bundle, installs production-only Pi dependencies, starts the agent on loopback, and runs FastAPI on Render’s assigned port. PostgreSQL is a Render-managed database. The public target is [lenny-growth-assistant-iau1.onrender.com](https://lenny-growth-assistant-iau1.onrender.com).

The deployment uses `RETRIEVAL_MODE=lexical`, a seeded transcript archive, and Gemini as the default provider. This avoids an Ollama embedding sidecar in the free service. It is a deliberate deployment tradeoff, not a semantic-vector equivalence claim. Gemini calls time out after 15 seconds and return a clearly labeled cited-excerpt fallback; this makes the product inspectable during quota/network incidents.

## Free-tier limits and submission procedure

Render can suspend an idle free web service. The first request may take roughly 50+ seconds. Open `/api/health` and a test conversation shortly before sharing the URL. Free-tier services are unsuitable for durable production traffic. Keep the repository as the reproducible source of truth and retain the local Compose path for the required Ollama demonstration.

Before submitting, verify the live health endpoint, a grounded answer or labeled fallback, source-card links, a second browser session’s isolation, and the repository’s secret scan. Upload the repository ZIP and screen recording to Drive, then place their verified sharing links beside the publisher URL in the submission form.
