# Security boundary

The deployment binds public ports to 127.0.0.1. It is designed for one evaluator, not a public multi-user installation. Session identifiers are not an authorization scheme. Public deployment requires authentication, ownership enforcement, TLS, rate limits, CSRF/origin review, migrations and backups.

## Generated content
Markdown is parsed without raw HTML. Images are omitted to prevent generated external image requests. Links open with noreferrer/noopener and React Markdown's safe URL handling.

HTML is sanitized with DOMPurify. Scripts, event handlers, forms, embeds, iframes, SVG/MathML, remote assets, meta refresh, base tags, and link navigation are removed. CSS may style the document, but CSS imports and URLs are stripped and network access is denied independently by CSP. The iframe has an empty sandbox: it has an opaque origin, no scripts, no navigation, no forms, and no parent storage/DOM access. This is intentionally stricter than the reference's allow-scripts example because the brief requires HTML/CSS, not executable apps. Downloads use the same sanitized HTML.

Source view is escaped text. No generated code runs in the host origin. DOMPurify tests are defense-in-depth checks, not a formal proof of zero vulnerabilities.

## Agent and data
The actual Pi SDK is restricted to zero tools, no extensions, no filesystem context discovery, and in-memory sessions. Only FastAPI accesses the database. Retrieved transcripts and conversation text are labeled as untrusted data. Model prompts alone are not a perfect injection defense; tool removal and output isolation limit consequences.

Queries are parameterized. Inputs and body/output sizes are bounded. Database advisory locks serialize each conversation. Error/latency logs exclude full prompts, transcripts, and keys. Credentials live in ignored local environment files. Cloud use requires explicit selection; no fallback can send local requests to Anthropic.

## Remaining risks
Citation ID checking cannot prove semantic entailment. Local models can misunderstand source passages or make unsupported inferences. A human should review important claims. A malicious local user already able to access the localhost API can read local sessions. This is documented scope, not a production tenant boundary.
