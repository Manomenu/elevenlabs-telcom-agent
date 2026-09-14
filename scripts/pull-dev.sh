#!/usr/bin/env bash
# Zaciąga do repo zmiany zrobione w dashboardzie ElevenLabs.
# Kierunek odwrotny do sync-dev.sh: dashboard -> repo.
#
#   ./scripts/pull-dev.sh          # branch dev (domyślnie)
#   ./scripts/pull-dev.sh nazwa    # inny branch
#
# Ściąga konfigurację agenta, treść procedur i definicje tooli, po czym
# pokazuje, co się zmieniło w plikach.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
command -v elevenlabs >/dev/null || { echo "Brak 'elevenlabs' w PATH. npm install -g @elevenlabs/cli" >&2; exit 1; }
PY=$(command -v python3 || command -v python) || { echo "Brak pythona w PATH." >&2; exit 1; }

exec "$PY" scripts/.internal/pull_dev.py "$@"
