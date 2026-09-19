# Submission checklist

| Required deliverable | Location / status |
|---|---|
| Full source | backend/, agent/, frontend/ |
| README and reproducible startup | README.md, docker-compose.yml, .env.example, scripts/setup.sh |
| Discovery and PRD | docs/PRD.md |
| Design | docs/design.md |
| Architecture | docs/architecture.md |
| Security and operational trade-offs | docs/security.md, README.md |
| Tests and actual evidence | backend/tests, agent/src/prompts.test.mjs, frontend/src/safety.test.ts, docs/verification.md |
| Coding-agent record with failures | agent_transcripts/ |
| Public GitHub repository | Pending owner's GitHub identity/authentication and final publication |
| Camera-on 2–3 minute video | User must record; script in docs/demo-script.md |
| YouTube link | Pending user recording/upload |
| Cloud live test | Pending valid ANTHROPIC_API_KEY in local .env |

Before publication: ensure .env, data/, .runtime/, dependencies, and model weights are not tracked. Review agent logs for secrets. Run tests, check source links, and confirm the README works from a clean checkout. Put repository and video URLs in this file when created.

The implementation is a local single-user take-home deployment. Do not represent it as a hardened public multi-tenant production service or claim unmeasured metrics.
