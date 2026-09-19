# Lenny Growth Assistant — Product requirements

## Discovery brief
Primary user: a growth product manager preparing a decision, experiment, or internal memo. Their job is to turn experienced operators' advice into a defensible next step without listening to hundreds of hours of interviews. The product reduces search and synthesis time while keeping evidence one click away.

## Success criteria (targets, not claimed results)
- At least 90% of factual claims in a manually reviewed 20-question evaluation are supported by their cited passages.
- At least 90% of deliberately unsupported questions are declined.
- Warm local first-token latency target: under 4 seconds; measure retrieval and generation separately. Long essays may take minutes on CPU. Never hide actual latency.
- 100% of tested session histories survive API restart and remain independent.
- No parent DOM/storage access, network requests, or navigation in the artifact attack fixtures. This is a testable scope, not a claim of zero possible vulnerabilities.
- An evaluator can start the stack with Docker Compose and run an explicitly documented first-time model download/index step.

## Assumptions and scope
Single-user local evaluation on Apple Silicon. No public hosted multi-tenant service, login, billing, web search, or arbitrary code execution. Bind exposed ports to localhost. Anonymous user metadata is persisted with sessions, not used as authentication. Transcript archive is a public educational resource; download separately, retain provenance, and do not redistribute it in this repository. The exact linked Ship 30 guide URL was absent from the pasted brief; use the publisher's beginner guide and document that choice. Its original atomic essay is 250 words; adapt its principles to the assignment's approximately 1,250-word output.

The take-home assignment controls conflicts: FastAPI, PostgreSQL, actual Pi Coding Agent integration, Ollama demo, and cloud integration are mandatory. Reference sample code is illustrative and must not be copied with its SQL, streaming, or sanitization defects.

## User flows and acceptance criteria
1. Create/select chat → ask a question → see retrieval status, streamed answer, citations with excerpt and source links. Reload restores history.
2. Follow up with a short reference → retrieval includes recent user context; each session has separate persisted history.
3. Select Ollama or Anthropic → selection is visible, applies to next request, and never silently falls back or sends local data to cloud.
4. Select Essay → a source-grounded, roughly 1,250-word Markdown document opens alongside chat; display word count and any length warning.
5. Select Markdown or HTML → artifact is persisted, previewable, downloadable, and available after reload. HTML is untrusted and isolated.
6. Empty archive, missing keys, unavailable services, timeout, and unsupported query produce useful states instead of fabricated success.

## Risks and decisions
Semantic relevance is not proof of factual support; combine minimum relevance, explicit evidence prompts, citation validation, and a manual claim-level evaluation. Small local models trade reasoning quality and speed for privacy and no API bill. Do not present a latency target as measured. Disable agent filesystem/shell tools. Use static HTML/CSS only with sanitization, iframe sandbox, and a deny-by-default CSP; interactive JavaScript is excluded. Database is the source of truth. Streaming failures persist an explicit failed status rather than a completed partial answer.

## Implementation sequence
Discovery docs → schema and ingestion → restricted Pi agent/model routing → streaming API and persistence → responsive artifact UI → automated and live verification → Desktop delivery and submission checklist.
