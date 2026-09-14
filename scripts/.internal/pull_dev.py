#!/usr/bin/env python3
"""Ściąga z platformy zmiany zrobione w dashboardzie i pokazuje, co przyszło.

Kierunek odwrotny do sync-dev.sh: dashboard → repo.

`elevenlabs agents pull` ściąga wyłącznie konfigurację agenta. Treść procedur
i definicje tooli żyją pod osobnymi endpointami i do plików configu nie trafiają,
więc zmiana procedury wyklikana w dashboardzie byłaby dla repo niewidzialna —
ten skrypt dociąga je do agent_configs/procedures/ i agent_configs/tools/.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from el_common import (
    BOLD,
    CYAN,
    DIM,
    GREEN,
    YELLOW,
    die,
    elevenlabs_bin,
    list_agents,
    list_branches,
)

ROOT = Path(__file__).resolve().parents[2]
PROC_DIR = ROOT / "agent_configs" / "procedures"
TOOL_DIR = ROOT / "agent_configs" / "tools"

# Adres ngroka jest tymczasowy — w repo trzymamy placeholder, żeby plik toola
# nie zmieniał się przy każdym restarcie tunelu.
PLACEHOLDER = "https://REPLACED_BY_SCRIPT"


def el(*args: str) -> dict:
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


def write_if_changed(path: Path, data: dict) -> bool:
    """Zapisuje plik tylko gdy treść faktycznie się różni.

    Bez tego każdy pull przestawiałby mtime wszystkich plików i git pokazywałby
    ruch tam, gdzie nic się nie zmieniło.
    """
    text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return True


def pull_config(agent_id: str) -> None:
    args = [
        "agents",
        "pull",
        "--agent",
        agent_id,
        "--all-branches",
        "--update",
        "--yes",
    ]
    r = subprocess.run(
        [elevenlabs_bin(), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if r.returncode != 0:
        die(f"pull nieudany:\n{(r.stderr or r.stdout).strip()}")


def pull_procedures(agent_id: str, branch_id: str) -> list[str]:
    """Ściąga treść każdej procedury. Lista zwraca metadane bez `content`."""
    listing = el(
        "agents", "procedures", "list", "--agent-id", agent_id, "--branch-id", branch_id
    )

    changed = []
    seen = set()
    for meta in listing.get("procedures", []):
        proc_id = meta.get("procedure_id") or meta.get("id")
        full = el(
            "agents",
            "procedures",
            "get",
            "--agent-id",
            agent_id,
            "--branch-id",
            branch_id,
            "--procedure-id",
            proc_id,
        )

        name = full.get("name") or meta.get("name")
        seen.add(name)
        spec = {
            "name": name,
            "type": full.get("type", "free_form"),
            "trigger": full.get("trigger"),
            "content": full.get("content", ""),
        }
        if write_if_changed(PROC_DIR / f"{name}.json", spec):
            changed.append(name)

    # Procedura usunięta w dashboardzie zostawiłaby w repo martwy plik, który
    # sync-dev.sh odtworzyłby przy następnym przebiegu.
    for path in PROC_DIR.glob("*.json"):
        if path.stem not in seen:
            print(
                f"  {YELLOW('!')} {path.name} — nie ma go na branchu "
                f"{DIM('(usunięty w dashboardzie?)')}"
            )

    return changed


def pull_tools(tool_ids: list[str]) -> list[str]:
    """Ściąga definicje tooli podpiętych do agenta, z URL-em na placeholder."""
    changed = []
    for tool_id in tool_ids:
        tool = el("agents", "tools", "get", "--tool-id", tool_id)
        config = tool.get("tool_config") or tool
        name = config.get("name")
        if not name:
            continue

        api = config.get("api_schema") or {}
        url = api.get("url", "")
        if "://" in url:
            # Zostawiamy samą ścieżkę, host zastępujemy placeholderem.
            api["url"] = PLACEHOLDER + "/" + url.split("://", 1)[1].split("/", 1)[-1]

        if write_if_changed(TOOL_DIR / f"{name.replace('_', '-')}.json", config):
            changed.append(name)
    return changed


def config_files_changed(before: dict[Path, str | None]) -> list[Path]:
    """Które pliki configu pull faktycznie zmienił.

    Porównujemy treść sprzed i po, a nie `git diff` — ten pokazywałby też
    zmiany z wcześniejszych przebiegów, które wciąż czekają w stage'u.
    """
    changed = []
    for path, old in before.items():
        new = path.read_text(encoding="utf-8") if path.exists() else None
        if new != old:
            changed.append(path)
    return changed


def snapshot(paths: list[Path]) -> dict[Path, str | None]:
    return {p: (p.read_text(encoding="utf-8") if p.exists() else None) for p in paths}


def main() -> int:
    branch_name = sys.argv[1] if len(sys.argv) > 1 else "dev"

    agents = list_agents()
    if not agents:
        die("Brak agentów na koncie.")
    agent = agents[0]
    agent_id = agent["agent_id"]

    branch = next(
        (b for b in list_branches(agent_id) if b.get("name") == branch_name), None
    )
    if not branch:
        die(f"Nie znaleziono brancha {branch_name!r}.")

    print(f"\n{BOLD('Agent:')} {agent.get('name')}")
    print(f"{BOLD('Branch:')} {CYAN(branch_name)} {DIM(branch['id'])}")

    if branch.get("draft_exists"):
        print(f"\n{YELLOW('! Branch ma niezapisany draft.')}")
        print(f"  {DIM('Ściągniemy ostatnią opublikowaną wersję, nie draft.')}")
        print(f"  {DIM('Zapisz zmiany w dashboardzie, żeby je tu zobaczyć.')}")

    config_files = sorted((ROOT / "agent_configs").glob("*.json"))
    before = snapshot(config_files)

    print(f"\n{DIM('1/3')} konfiguracja agenta")
    pull_config(agent_id)

    print(f"{DIM('2/3')} procedury")
    changed_procs = pull_procedures(agent_id, branch["id"])
    for name in changed_procs:
        print(f"  {GREEN('~')} {name}")

    print(f"{DIM('3/3')} toole")
    config_file = (
        ROOT / "agent_configs" / f"Telecommunication-platform-agent.{branch_name}.json"
    )
    tool_ids = []
    if config_file.exists():
        data = json.loads(config_file.read_text(encoding="utf-8"))
        tool_ids = data["conversation_config"]["agent"]["prompt"].get("tool_ids", [])
    changed_tools = pull_tools(tool_ids)
    for name in changed_tools:
        print(f"  {GREEN('~')} {name}")

    changed_configs = config_files_changed(before)

    print()
    total = len(changed_configs) + len(changed_procs) + len(changed_tools)
    if total == 0:
        print(f"{DIM('Bez zmian — repo jest zgodne z platformą.')}")
        return 0

    print(BOLD(f"Zmienione pliki ({total}):"))
    for path in changed_configs:
        print(f"  {GREEN('~')} agent_configs/{path.name}")
    for name in changed_procs:
        print(f"  {GREEN('~')} agent_configs/procedures/{name}.json")
    for name in changed_tools:
        print(f"  {GREEN('~')} agent_configs/tools/{name.replace('_', '-')}.json")
    print(f"\n{DIM('Szczegóły:')} git diff agent_configs/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
