# Build record: initial scaffolding

Date: 2026-09-18/19. The implementation was generated and verified by a coding agent under human direction. The project began in an empty workspace.

Decisions made:

- Used FastAPI, PostgreSQL/pgvector, React/Vite, Docker Compose, Ollama, and Pi Coding Agent SDK 0.73.1.
- Kept Pi sessions in memory and disabled its built-in tools, extensions, skills, prompt templates, and filesystem-context discovery. FastAPI owns retrieval and persistence.
- Downloaded the public ChatPRD archive at a pinned commit and recorded its SHA-256 manifest. Source material and vector data remain ignored from Git.
- Implemented static, sandboxed HTML artifacts instead of executable artifacts. Scripts and remote resource loading are not required by the take-home brief and create an unnecessary trust boundary.

Validation performed: backend, frontend, agent, Compose image build, PostgreSQL/pgvector integration, live local model, source rendering, and responsive UI checks. See `docs/verification.md` for results.
