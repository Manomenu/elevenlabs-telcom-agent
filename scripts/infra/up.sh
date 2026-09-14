#!/usr/bin/env bash
# Stawia infrastrukturę projektu (backend webhooków + tunel ngrok)
# i wypisuje publiczny URL do wklejenia w konfiguracji toola ElevenLabs.
#
#   ./scripts/infra/up.sh            # start
#   ./scripts/infra/up.sh --rebuild  # przebuduj obraz backendu
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

command -v docker >/dev/null || { echo "Brak dockera w PATH." >&2; exit 1; }
[ -f .env ] || { echo "Brak .env. Skopiuj .env.example i uzupełnij NGROK_AUTHTOKEN." >&2; exit 1; }
grep -q '^NGROK_AUTHTOKEN=.\+' .env || { echo "NGROK_AUTHTOKEN nie ustawiony w .env" >&2; exit 1; }

BUILD_ARGS=()
[[ "${1:-}" == "--rebuild" ]] && BUILD_ARGS+=(--build)

echo "==> Start serwisów"
docker compose up -d "${BUILD_ARGS[@]}"

echo "==> Czekam na tunel ngrok"
NGROK_API="http://localhost:14040/api/tunnels"
PUBLIC_URL=""
for _ in $(seq 1 30); do
  # ngrok publikuje adres dopiero po zestawieniu tunelu, więc odpytujemy
  # jego lokalne API aż pojawi się wpis https.
  PUBLIC_URL=$(curl -s --max-time 3 "$NGROK_API" 2>/dev/null \
    | grep -o '"public_url":"https://[^"]*"' \
    | head -1 | cut -d'"' -f4 || true)
  [ -n "$PUBLIC_URL" ] && break
  sleep 2
done

if [ -z "$PUBLIC_URL" ]; then
  echo "✗ Nie udało się odczytać adresu ngroka. Logi:" >&2
  docker compose logs --tail 30 ngrok >&2
  exit 1
fi

# Zapisujemy adres, żeby inne skrypty (np. podpięcie toola) nie musiały
# ponownie odpytywać ngroka.
mkdir -p .artifacts
printf '%s\n' "$PUBLIC_URL" > .artifacts/ngrok-url.txt

# Stan, porty i linki wypisuje list.sh — jedno miejsce, jeden format.
"$ROOT/scripts/infra/list.sh"

echo "Adres zapisany w .artifacts/ngrok-url.txt"
echo "Po restarcie tunelu uruchom ./scripts/sync-dev.sh — adres się zmienił."
