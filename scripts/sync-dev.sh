#!/usr/bin/env bash
# Wysyła na branch dev wszystko, co trzymamy w repo:
#   1. tool check_if_serviceable (z aktualnym adresem ngroka)
#   2. procedury z agent_configs/procedures/
#   3. podpięcie toola do agenta + publikacja draftów
#   4. post-call webhook register-call (wymaga webhooks_write na kluczu)
#   5. pull, żeby repo dogoniło stan
#
#   ./scripts/sync-dev.sh          # branch dev (domyślnie)
#   ./scripts/sync-dev.sh nazwa    # inny branch
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
BRANCH="${1:-dev}"
PY=$(command -v python3 || command -v python) || { echo "Brak pythona w PATH." >&2; exit 1; }

[ -f .artifacts/ngrok-url.txt ] || { echo "Brak adresu ngroka — najpierw ./scripts/infra/up.sh" >&2; exit 1; }

echo "==> 1/5 Tool"
"$PY" scripts/.internal/sync_tool.py

echo; echo "==> 2/5 Procedury"
"$PY" scripts/.internal/sync_procedures.py "$BRANCH"

echo; echo "==> 3/5 Podpięcie toola i publikacja"
"$PY" scripts/.internal/attach_and_publish.py "$BRANCH"

echo; echo "==> 4/5 Post-call webhook"
# Brak uprawnienia webhooks_write nie ma przerywać reszty synchronizacji.
"$PY" scripts/.internal/sync_postcall.py "$BRANCH" || \
  echo "   (pominięte — patrz komunikat wyżej)"

echo; echo "==> 5/5 Pull do repo"
elevenlabs agents pull --all --all-branches --update --yes >/dev/null

echo
echo "✓ Gotowe. Różnice Main vs $BRANCH:"
diff <("$PY" -m json.tool agent_configs/Telecommunication-platform-agent.json) \
     <("$PY" -m json.tool "agent_configs/Telecommunication-platform-agent.$BRANCH.json") \
  | head -5 || true
