#!/usr/bin/env bash
# Zatrzymuje infrastrukturę projektu.
#
#   ./scripts/infra/down.sh          # stop
#   ./scripts/infra/down.sh --clean  # stop + usuń log i zapisany adres ngroka
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

command -v docker >/dev/null || { echo "Brak dockera w PATH." >&2; exit 1; }

echo "==> Zatrzymuję serwisy"
docker compose down

if [[ "${1:-}" == "--clean" ]]; then
  echo "==> Czyszczę artefakty"
  rm -f .artifacts/agent.log .artifacts/ngrok-url.txt
fi

echo "✓ Gotowe."
