#!/usr/bin/env python3
"""Interaktywny pull: wybierz agenta, potem brancha, potem ściągnij config.

./scripts/pull-agent.sh          # wybór agenta -> wybór brancha
./scripts/pull-agent.sh --all    # wybór agenta -> wszystkie branche, bez pytania
"""

import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from el_common import (
    BOLD,
    CYAN,
    DIM,
    GREEN,
    RED,
    YELLOW,
    die,
    elevenlabs_bin,
    fmt_branch,
    list_agents,
    list_branches,
    pick,
)


def run_pull(agent_id: str) -> int:
    """Ściąga agenta wraz ze wszystkimi branchami.

    Świadomie NIE używamy `--branch <id>`: CLI rejestruje wtedy brancha pod
    jego ID zamiast nazwy, tworząc w agents.json drugi wpis obok istniejącego
    ('dev' i 'agtbrch_...' jako osobne branche) i przestawiając główny
    `config` na wersję z tego brancha. `--all-branches` nazywa je poprawnie.

    `--update` jest konieczne, bo bez niego pull pomija agenta, który już jest
    w agents.json, i kończy się kodem 0 nic nie ściągnąwszy.
    """
    args = ["--agent", agent_id, "--all-branches", "--update", "--yes"]
    print(f"\n{DIM('$ elevenlabs agents pull ' + ' '.join(args))}\n")

    r = subprocess.run(
        [elevenlabs_bin(), "agents", "pull", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    out = (r.stdout or "") + (r.stderr or "")
    print(out.rstrip())

    if r.returncode == 0 and "0 created, 0 updated" in out:
        print(YELLOW("\n! CLI nic nie zaktualizowało (0 created, 0 updated)."))
    return r.returncode


def main() -> int:
    skip_branch_pick = "--all" in sys.argv[1:]

    agents = list_agents()
    if not agents:
        die("Brak agentów na koncie.")

    print(f"\n{BOLD('Wybierz agenta:')}\n")
    agent = pick(
        agents,
        lambda a: f"{a.get('name', '(bez nazwy)'):<40} {DIM(a['agent_id'])}",
        "Agent",
    )
    agent_id = agent["agent_id"]

    branches = list_branches(agent_id)
    if not branches:
        die(f"Agent {agent_id} nie ma branchy.")

    target = None
    if not skip_branch_pick:
        print(f"\n{BOLD('Wybierz brancha:')}\n")
        target = pick(branches, fmt_branch, "Branch")

        if target.get("draft_exists"):
            print(f"\n{YELLOW('! Ten branch ma niezacommitowany draft.')}")
            print(f"  {DIM('Pull ściągnie ostatnią opublikowaną wersję, nie draft.')}")

    label = CYAN(target["name"]) if target else DIM("wszystkie branche")
    print(f"\n{BOLD('Pull:')} {agent.get('name')} / {label}")

    rc = run_pull(agent_id)
    if rc != 0:
        print(RED(f"\n✗ Pull zakończony kodem {rc}"))
        return rc

    # Pull zawsze ściąga komplet branchy; podpowiedz plik tego wybranego.
    print(GREEN("\n✓ Gotowe."))
    if target:
        print(f"  {DIM('Plik brancha:')} agent_configs/*.{target['name']}.json")
    print(f"  {DIM('Sprawdź zmiany:')} git diff agent_configs/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
