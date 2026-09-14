#!/usr/bin/env bash
# Pokazuje, co stoi z infrastruktury: stan serwisów, porty i linki.
#
#   ./scripts/infra/list.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
PY=$(command -v python3 || command -v python) || { echo "Brak pythona w PATH." >&2; exit 1; }

exec "$PY" scripts/.internal/infra_list.py "$@"
