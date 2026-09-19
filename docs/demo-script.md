# Camera-on demo (2–3 minutes)

Preparation: complete setup, confirm green local status, load two example conversations (answer and essay/artifact). Keep camera visible in recording. Use `Record Demo.command` from the project root to launch a three-minute macOS screen-and-microphone capture, then enable a camera overlay in the macOS capture controls (or use QuickTime/OBS picture-in-picture). Do not show `.env`, terminals, or API keys. The assignment requires your own camera presence and YouTube upload; these cannot be replaced by an agent-generated recording.

## Recording checklist

- Keep the browser on `http://127.0.0.1:3000`, with the **Ollama · Local** provider selected.
- Use the built-in screenshot toolbar to capture only the Lenny browser window; turn on microphone, click indicators, and camera overlay.
- Show one cited answer, one follow-up, a persisted second conversation, a Ship 30 essay, and an HTML or Markdown artifact preview.
- Show an unsupported question so the evaluator sees the explicit abstention behavior.
- Do not open `.env`, Docker logs, a terminal, or any view containing credentials.
- Stop at about 2:45–3:00, check playback, then upload the resulting `.mov` to YouTube as Unlisted unless the evaluator specifies another setting.

0:00–0:20 — “A growth PM needs usable, defensible advice without listening to hundreds of hours of interviews. This assistant retrieves original transcript passages, preserves their source, and turns them into answers and working documents.”

0:20–0:55 — Show Ollama · Local selector and system status. Ask “How does Rahul Vohra measure product-market fit?” Show streaming, expand one citation, compare the answer with its exact source passage. Mention actual measured latency, not the aspirational target.

0:55–1:15 — Ask a follow-up. Show another conversation, return, and reload to demonstrate persisted independent histories.

1:15–1:50 — Show a saved essay with word count and source references. Explain the dedicated Ship 30 rubric. Open an HTML artifact beside the chat, switch Preview/Source, and download it.

1:50–2:15 — Ask an unsupported question and show abstention. Explain HTML is static: sanitized, sandboxed, no scripts/network/parent access.

2:15–2:45 — “The main trade-off is a small local model: private and inexpensive, with weaker instruction-following and longer essays taking more time. Pi handles agent inference, while FastAPI controls evidence and persistence. Cloud is an explicit selection and never a silent fallback.” Show README's Compose startup and verification report.

2:45–3:00 — Close with known limitations and where the evaluator finds source, docs, tests, and setup.

Upload to your YouTube account, choose visibility compatible with the evaluator's instructions, and put the resulting link in the submission checklist/README. Verify the link in a signed-out browser before submitting.
