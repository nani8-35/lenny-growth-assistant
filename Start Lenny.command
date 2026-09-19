#!/bin/zsh
set -e
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd -P)"
cd "$PROJECT_DIR"

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker Desktop is required. Install and start it, then run this launcher again."
  read -n 1 -s -r '?Press any key to close.'
  exit 1
fi

if command -v ollama >/dev/null 2>&1; then
  OLLAMA_BIN="$(command -v ollama)"
elif [ -x "$PROJECT_DIR/../.setup/ollama/ollama" ]; then
  OLLAMA_BIN="$PROJECT_DIR/../.setup/ollama/ollama"
else
  echo "Ollama is required. Install it, pull the models listed in README.md, then run this launcher again."
  read -n 1 -s -r '?Press any key to close.'
  exit 1
fi

if ! curl -fsS http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
  nohup "$OLLAMA_BIN" serve >/tmp/lenny-ollama.log 2>&1 &
  sleep 2
fi

docker compose up -d --build
open http://127.0.0.1:3000
