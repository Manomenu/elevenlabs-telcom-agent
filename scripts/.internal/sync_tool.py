#!/usr/bin/env python3
"""Tworzy lub aktualizuje webhook tool w ElevenLabs z aktualnym adresem ngroka.

Adres ngroka zmienia się przy każdym restarcie tunelu, więc definicja toola w
repo trzyma placeholder, a ten skrypt podstawia bieżący URL przed wysyłką.

Toole są workspace-level (nie branch-scoped), więc tool powstaje raz; do agenta
na konkretnym branchu podpina go attach_tool.py przez prompt.tool_ids.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from el_common import BOLD, DIM, GREEN, die, elevenlabs_bin

ROOT = Path(__file__).resolve().parents[2]
TOOL_DIR = ROOT / "agent_configs" / "tools"
NGROK_URL_FILE = ROOT / ".artifacts" / "ngrok-url.txt"
PLACEHOLDER = "https://REPLACED_BY_SCRIPT"


def public_url() -> str:
    if not NGROK_URL_FILE.exists():
        die("Brak .artifacts/ngrok-url.txt — najpierw ./scripts/infra/up.sh")
    url = NGROK_URL_FILE.read_text(encoding="utf-8").strip().rstrip("/")
    if not url.startswith("https://"):
        die(f"Niepoprawny adres ngroka: {url!r}")
    return url


def el_json(*args: str) -> dict:
    """Wywołuje CLI i zwraca JSON. Błąd kończy skrypt z treścią odpowiedzi."""
    r = subprocess.run(
        [elevenlabs_bin(), *args, "--format", "json"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if r.returncode != 0:
        die(f"{' '.join(args)}\n{(r.stderr or r.stdout).strip()}")
    return json.loads(r.stdout) if r.stdout.strip() else {}


def find_existing(name: str) -> str | None:
    data = el_json("agents", "tools", "list")
    for tool in data.get("tools", []):
        config = tool.get("tool_config") or {}
        if config.get("name") == name:
            return tool.get("id") or tool.get("tool_id")
    return None


def sync_one(path: Path, url: str) -> tuple[str, str]:
    """Wysyła jeden plik definicji. Zwraca (nazwa, tool_id)."""
    spec = json.loads(path.read_text(encoding="utf-8"))
    spec["api_schema"]["url"] = spec["api_schema"]["url"].replace(PLACEHOLDER, url)

    name = spec["name"]
    print(f"\n{BOLD(name)}  {DIM(path.name)}")
    print(f"  {DIM('URL:')} {spec['api_schema']['url']}")

    existing = find_existing(name)
    payload = json.dumps({"tool_config": spec})

    if existing:
        print(f"  {DIM('istnieje')} ({existing}) — aktualizuję")
        el_json("agents", "tools", "update", "--tool-id", existing, "--params", payload)
        return name, existing

    print(f"  {DIM('nie istnieje')} — tworzę")
    created = el_json("agents", "tools", "create", "--params", payload)
    tool_id = created.get("id") or created.get("tool_id")
    if not tool_id:
        die(f"Nie udało się ustalić ID toola {name!r}.")
    return name, tool_id


def main() -> int:
    # Każdy plik w katalogu to osobny tool — dodanie nowego nie wymaga
    # zmiany tego skryptu.
    files = sorted(TOOL_DIR.glob("*.json"))
    if not files:
        die(f"Brak definicji tooli w {TOOL_DIR}")

    url = public_url()
    ids_file = ROOT / ".artifacts" / "tool-ids.json"
    ids = json.loads(ids_file.read_text(encoding="utf-8")) if ids_file.exists() else {}

    for path in files:
        name, tool_id = sync_one(path, url)
        # ID zapisujemy po nazwie, żeby attach_and_publish.py nie musiał
        # szukać toola po nazwie przy każdym uruchomieniu.
        ids[name] = tool_id

    ids_file.parent.mkdir(parents=True, exist_ok=True)
    ids_file.write_text(json.dumps(ids, indent=2), encoding="utf-8")

    print(GREEN(f"\n✓ {len(files)} tool(i) zsynchronizowane"))
    for name, tool_id in ids.items():
        print(f"  {name} → {DIM(tool_id)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
