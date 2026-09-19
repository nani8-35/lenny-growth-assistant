# Security boundary

## Local and temporary public scopes

The Compose deployment binds public ports to localhost and is intended for a single local evaluator. The temporary Render URL is public for assessment review only. It uses a browser-generated workspace token (`X-Workspace-Token`) stored in `localStorage`; FastAPI requires that token to create, list, read, chat in, or retrieve an artifact from a session. Sessions with a different or missing token return `404`. Existing legacy rows without an owner token are not publicly listed.

This is session isolation, not authentication. It does not protect a visitor who shares their browser token or device, provide account recovery, rate limiting, audit identities, backup/retention controls, or a multi-tenant authorization boundary. Add a real identity provider, server-side rate limiting, CSRF/origin review, TLS/domain policy, migrations, backups, and deletion policy before any non-evaluation public launch.

## Generated content

Markdown is rendered without raw HTML or images. Links use safe URL handling and `noopener noreferrer`.

HTML is sanitized with DOMPurify. Scripts, event handlers, forms, embeds, iframes, SVG/MathML, remote assets, meta refresh, base tags, and link navigation are removed. CSS imports and URLs are stripped; the iframe has an empty sandbox, opaque origin, no navigation, no forms, no scripts, and no parent DOM/storage access. Source view is escaped text. DOMPurify tests are defense in depth, not a formal proof of safety.

## Agent, data, and secrets

The Pi SDK runs with zero tools, extensions, skills discovery, filesystem context discovery, and persistent agent sessions. Only FastAPI accesses the database. Inputs, output sizes, and conversation concurrency are bounded; parameterized queries and advisory locks protect persistence. Structured logs retain request IDs, durations, counts, and error classes, never complete prompts, excerpts, or secret values.

Secrets belong in ignored `.env` files or Render secret environment variables. A tracked-source audit must never reveal a key. Gemini receives only the selected question, recent conversation, and retrieved archive excerpts. Gemini failure falls back to labeled local archive excerpts; Ollama and Claude never silently switch providers.

## Evidence integrity

Citation IDs are constrained to retrieved source IDs, but identifier validation cannot prove semantic entailment. The UI exposes source cards and the evaluation rubric requires claim-level reviewer checks. Important advice must be reviewed against the underlying transcript.
