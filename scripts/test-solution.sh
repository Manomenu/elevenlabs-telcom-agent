#!/usr/bin/env bash
# Weryfikacja całego repo: lint, formatowanie, typy, składnia konfiguracji.
#
#   ./scripts/test-solution.sh          # sprawdza
#   ./scripts/test-solution.sh --fix    # + autopoprawki ruffa i formatowanie
#
# Nie wymaga stojącej infrastruktury. Kod wyjścia 1, gdy cokolwiek zawiedzie —
# nadaje się do CI i do hooka pre-commit.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FIX=0
[[ "${1:-}" == "--fix" ]] && FIX=1

PY=$(command -v python3 || command -v python) || { echo "Brak pythona w PATH." >&2; exit 1; }

# Kolory tylko na terminalu — w CI czysty tekst.
if [ -t 1 ]; then
  BOLD=$'\033[1m'; DIM=$'\033[90m'; GREEN=$'\033[32m'
  RED=$'\033[31m'; YELLOW=$'\033[33m'; OFF=$'\033[0m'
else
  BOLD=""; DIM=""; GREEN=""; RED=""; YELLOW=""; OFF=""
fi

FAILED=()
SKIPPED=()

step() { printf '\n%s==> %s%s\n' "$BOLD" "$1" "$OFF"; }
ok()   { printf '%s  ✓ %s%s\n' "$GREEN" "$1" "$OFF"; }
bad()  { printf '%s  ✗ %s%s\n' "$RED" "$1" "$OFF"; FAILED+=("$1"); }
skip() { printf '%s  ⊘ %s%s\n' "$YELLOW" "$1" "$OFF"; SKIPPED+=("$1"); }

# ── 1. ruff: lint ──────────────────────────────────────────────────────
step "ruff check"
if "$PY" -m ruff --version >/dev/null 2>&1; then
  if [ $FIX -eq 1 ]; then
    "$PY" -m ruff check --fix . && ok "lint (z autopoprawkami)" || bad "ruff check"
  else
    "$PY" -m ruff check . && ok "lint" || bad "ruff check"
  fi
else
  skip "ruff niezainstalowany (pip install ruff)"
fi

# ── 2. ruff: formatowanie ──────────────────────────────────────────────
step "ruff format"
if "$PY" -m ruff --version >/dev/null 2>&1; then
  if [ $FIX -eq 1 ]; then
    "$PY" -m ruff format . && ok "sformatowane" || bad "ruff format"
  else
    "$PY" -m ruff format --check . && ok "formatowanie" || bad "ruff format --check"
  fi
else
  skip "ruff niezainstalowany"
fi

# ── 3. pyright: typy ───────────────────────────────────────────────────
# Ten sam silnik, którego w edytorze używa Pylance — łapie to, co widać
# jako czerwone podkreślenia, zanim trafi to do repo.
step "pyright"
if command -v npx >/dev/null 2>&1; then
  if npx --yes pyright; then
    ok "typy"
  else
    bad "pyright"
  fi
else
  skip "npx niedostępny — pyright pominięty"
fi

# ── 4. składnia plików konfiguracyjnych ────────────────────────────────
# Literówka w JSON-ie agenta albo w compose ujawniłaby się dopiero przy
# wysyłce na platformę lub przy starcie kontenera.
step "konfiguracja"
"$PY" - <<'PYEOF'
import json
import sys
import tomllib
from pathlib import Path

failed = []

for path in sorted(Path("agent_configs").rglob("*.json")) + [
    Path("agents.json"),
    Path("pyrightconfig.json"),
]:
    if not path.exists():
        continue
    try:
        json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as err:
        failed.append(f"{path}: {err}")

for path in sorted(Path().glob("**/*.toml")):
    if ".venv" in path.parts:
        continue
    try:
        tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as err:
        failed.append(f"{path}: {err}")

for line in failed:
    print(f"  {line}")
sys.exit(1 if failed else 0)
PYEOF
[ $? -eq 0 ] && ok "JSON i TOML" || bad "składnia konfiguracji"

# ── 5. docker compose ──────────────────────────────────────────────────
step "docker compose"
if command -v docker >/dev/null 2>&1; then
  if docker compose config >/dev/null 2>&1; then
    ok "compose poprawny"
  else
    # Bez .env compose nie rozwinie NGROK_AUTHTOKEN — to nie błąd pliku.
    if [ ! -f .env ]; then
      skip "brak .env (compose wymaga NGROK_AUTHTOKEN)"
    else
      bad "docker compose config"
    fi
  fi
else
  skip "docker niedostępny"
fi

# ── 6. skrypty powłoki ─────────────────────────────────────────────────
step "składnia .sh"
SH_BAD=0
for script in scripts/*.sh scripts/infra/*.sh; do
  bash -n "$script" || { echo "  $script"; SH_BAD=1; }
done
[ $SH_BAD -eq 0 ] && ok "wszystkie skrypty" || bad "składnia .sh"

# ── podsumowanie ───────────────────────────────────────────────────────
printf '\n%s────────────────────────────────────%s\n' "$DIM" "$OFF"
for name in "${SKIPPED[@]:-}"; do
  [ -n "$name" ] && printf '%s  ⊘ pominięte: %s%s\n' "$YELLOW" "$name" "$OFF"
done

if [ ${#FAILED[@]} -eq 0 ]; then
  printf '%s  ✓ wszystko przeszło%s\n\n' "$GREEN" "$OFF"
  exit 0
fi

printf '%s  ✗ nieudane: %s%s\n\n' "$RED" "${FAILED[*]}" "$OFF"
[ $FIX -eq 0 ] && printf '%s  Część naprawi: ./scripts/test-solution.sh --fix%s\n\n' "$DIM" "$OFF"
exit 1
