#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f .env ] || cp .env.example .env
command -v docker >/dev/null || { echo 'Install Docker Desktop first.'; exit 1; }
command -v ollama >/dev/null || { echo 'Install Ollama first.'; exit 1; }
ollama pull llama3.1:8b
ollama pull nomic-embed-text
ollama create lenny-growth:8b -f Modelfile
docker compose up --build -d
docker compose exec -T backend python -m scripts.download_transcripts --output /data/transcripts
docker compose exec -T backend python -m scripts.ingest --path /data/transcripts
echo 'Ready: http://localhost:3000'
