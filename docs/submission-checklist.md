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
| Public GitHub repository | https://github.com/nani8-35/lenny-growth-assistant |
| Camera-on 2–3 minute video | User must record; script in docs/demo-script.md |
| YouTube link | Pending user recording/upload |
| Cloud live test | Integration and key handoff verified; live generation is blocked until the Anthropic account has API credit |

Before final submission: ensure .env, data/, .runtime/, dependencies, and model weights are not tracked. Review agent logs for secrets. Run tests, check source links, confirm the README works from a clean checkout, and add the verified YouTube URL here after upload.

The implementation is a local single-user take-home deployment. Do not represent it as a hardened public multi-tenant production service or claim unmeasured metrics.
