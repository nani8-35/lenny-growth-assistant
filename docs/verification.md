# Verification record

Recorded locally on 2026-09-19 on Apple Silicon (M5, 12 GB unified GPU memory available). The application was started with Docker Compose, PostgreSQL 16 with pgvector, native Ollama, and the restricted Pi Coding Agent service.

## Completed checks

| Check | Result |
|---|---|
| Backend unit and API validation tests | 7 passed, 2 skips when a dedicated database is not supplied |
| Backend including PostgreSQL/pgvector and chat persistence integration | 9 passed against `lenny_test` |
| Agent provider/skill tests | 4 passed |
| Frontend artifact/SSE security tests | 3 passed |
| Frontend TypeScript production build | Passed |
| Docker Compose build | Passed |
| Live health check | Database, Pi agent, native Ollama, 8B local model, embedding model, and vector index ready |
| Responsive browser check | Desktop and 390 px layout inspected |
| Live grounded answer | 8B answer streamed, six source cards persisted with its conversation |
| Live Markdown artifact | Generated, persisted, and available to the artifact viewer |

The full transcript archive was indexed idempotently from the manifest commit in `data/transcripts/manifest.json`: 303 episodes and 15,250 passages. The health endpoint reports these exact counts.

## Measured local model behavior

The original 3B smoke response first token was 6.418 seconds and total time was 12.878 seconds on a focused index. It missed the PRD's under-four-second aspiration and can produce weak or over-broad synthesis even with source IDs. The final 8B smoke response completed with source IDs, no warnings, a 15.905-second first token, and 48.079 seconds total time. The final Markdown artifact response completed with source IDs in 40.315 seconds. These values are actual observed results, not benchmarks. The implementation makes citations visible and validates citation identifiers, but it cannot prove a source entails a claim; perform the claim-level human review in `evaluation.md` before submission.

## Failure record and correction

1. A first 3B response omitted inline citations and made an incorrect inference. The app now passes the exact valid citation IDs to the model, instructs a revision pass when citations are absent, replaces the draft in the stream, and withholds a response if citations remain invalid.
2. The local server and containers stopped during a desktop-session reset. Docker volumes, local model weights, and downloaded transcripts persisted; the stack was rebuilt and restarted successfully.
3. The cloud path was rechecked after a local `ANTHROPIC_API_KEY` was configured. The key reached Anthropic successfully, but Anthropic returned `invalid_request_error` because the account's API credit balance is too low. The failure is an account-billing condition, not a fallback or local configuration failure; no cloud generation was completed or claimed.

## Remaining owner actions

Add Anthropic API credits, rerun the cloud smoke test, record the required camera-on demo, and upload the YouTube video. These cannot be honestly completed without the owner's account access and presence.
