#!/usr/bin/env bash
# Interaktywny pull configu agenta: wybór agenta -> wybór brancha -> pull.
#
#   ./scripts/pull-agent.sh                 # wybór agenta, potem brancha
#   ./scripts/pull-agent.sh --all           # wybór agenta, potem wszystkie branche bez pytania
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
command -v elevenlabs >/dev/null || { echo "Brak 'elevenlabs' w PATH. npm install -g @elevenlabs/cli" >&2; exit 1; }
PY=$(command -v python3 || command -v python) || { echo "Brak pythona w PATH." >&2; exit 1; }

exec "$PY" "$DIR/.internal/pull_agent.py" "$@"
