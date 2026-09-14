#!/usr/bin/env python3
"""Wysyła procedury z agent_configs/procedures/ na wskazany branch agenta.

Procedury SĄ branch-scoped (w odróżnieniu od tooli), więc każda operacja
wymaga --agent-id i --branch-id. Create zapisuje draft, więc na końcu
publikujemy drafty w wersję.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from el_common import (
    BOLD,
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


def el_json(*args: str, body: dict | None = None) -> dict:
    """Wywołuje CLI; body idzie przez stdin (`--json -`), nie jako argument.

    Treść procedury bywa długa, a Windows ma limit długości linii poleceń —
    przekazana w argumencie kończy się błędem "The system cannot find the
    file specified".
    """
    cmd = [elevenlabs_bin(), *args, "--format", "json"]
    stdin_data = None
    if body is not None:
        cmd += ["--json", "-"]
        stdin_data = json.dumps(body)

    r = subprocess.run(
        cmd,
        input=stdin_data,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if r.returncode != 0:
        die(f"{' '.join(args)}\n{(r.stderr or r.stdout).strip()}")
    return json.loads(r.stdout) if r.stdout.strip() else {}


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
    branch_id = branch["id"]

    print(f"\n{BOLD('Agent:')} {agent.get('name')}")
    print(f"{BOLD('Branch:')} {branch_name} {DIM(branch_id)}")

    existing = el_json(
        "agents", "procedures", "list", "--agent-id", agent_id, "--branch-id", branch_id
    )
    by_name = {
        p.get("name"): p.get("procedure_id") or p.get("id")
        for p in existing.get("procedures", existing.get("results", []))
    }

    files = sorted(PROC_DIR.glob("*.json"))
    if not files:
        die(f"Brak plików procedur w {PROC_DIR}")

    for path in files:
        spec = json.loads(path.read_text(encoding="utf-8"))
        name = spec["name"]

        if name in by_name:
            # Edycja istniejącej procedury idzie przez jej draft, nie przez create.
            print(f"  {YELLOW('~')} {name} — istnieje, aktualizuję draft")
            print(f"    {DIM(by_name[name])}")
            el_json(
                "agents",
                "procedures",
                "drafts",
                "update",
                "--agent-id",
                agent_id,
                "--branch-id",
                branch_id,
                "--procedure-id",
                by_name[name],
                body=spec,
            )
        else:
            print(f"  {GREEN('+')} {name} — tworzę")
            created = el_json(
                "agents",
                "procedures",
                "create",
                "--agent-id",
                agent_id,
                "--branch-id",
                branch_id,
                body=spec,
            )
            print(f"    {DIM(created.get('procedure_id', ''))}")

    print(GREEN("\n✓ Procedury wysłane jako drafty."))
    print(f"  {DIM('Publikuje je następny krok: attach_and_publish.py')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
