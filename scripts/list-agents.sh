#!/usr/bin/env bash
# Listuje agentów ElevenLabs wraz z ich branchami.
#
#   ./scripts/list-agents.sh          # czytelna tabela
#   ./scripts/list-agents.sh --json   # surowy JSON (agenci z zagnieżdżonymi branchami)
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
command -v elevenlabs >/dev/null || { echo "Brak 'elevenlabs' w PATH. npm install -g @elevenlabs/cli" >&2; exit 1; }
PY=$(command -v python3 || command -v python) || { echo "Brak pythona w PATH." >&2; exit 1; }

exec "$PY" "$DIR/.internal/list_agents.py" "$@"
