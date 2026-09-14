#!/usr/bin/env bash
# Ładuje artykuły SuwalkiCable do knowledge base ElevenLabs, indeksuje je
# dla RAG-a i podpina do agenta na wskazanym branchu.
#
#   ./scripts/kb/seed.sh          # branch dev (domyślnie)
#   ./scripts/kb/seed.sh nazwa    # inny branch
#
# Źródło treści: agent_configs/knowledge-base/articles.json
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
command -v elevenlabs >/dev/null || { echo "Brak 'elevenlabs' w PATH. npm install -g @elevenlabs/cli" >&2; exit 1; }
PY=$(command -v python3 || command -v python) || { echo "Brak pythona w PATH." >&2; exit 1; }

exec "$PY" scripts/.internal/kb_seed.py "$@"
