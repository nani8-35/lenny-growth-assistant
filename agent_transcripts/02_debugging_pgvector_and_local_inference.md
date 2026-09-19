# Build record: pgvector and local inference correction

The ingestion pipeline initially indexed a focused set of transcripts to establish end-to-end retrieval, then resumed a full idempotent pass. Each episode replaces its chunks only after all local embeddings are available.

Two useful failures were retained:

1. The base 3B model produced an answer without inline citations, and one earlier direct test reversed the meaning of an evidence threshold. This was not accepted as a successful grounded answer. The agent prompt and stream now add a revision pass for missing citation IDs; FastAPI refuses uncited non-abstaining output. The larger 8B model is recommended for final evaluation, with a human claim-level check.
2. A Docker restart initially exposed a local shell path issue for the credential helper. Starting Docker through its application resources resolved it. The complete Compose build and integration tests then passed.

No credentials, user prompts, or private data are included in this record.
