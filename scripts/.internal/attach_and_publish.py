#!/usr/bin/env python3
"""Podpina tool do agenta na branchu dev i publikuje drafty procedur w wersję.

Toole są workspace-level, więc "podpięcie" to dopisanie ich id do
conversation_config.agent.prompt.tool_ids — a to pole JEST branch-scoped.
Ten sam PATCH publikuje oczekujące drafty procedur.
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
TOOL_IDS_FILE = ROOT / ".artifacts" / "tool-ids.json"


def el(*args: str, body: dict | None = None) -> dict:
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

    if not TOOL_IDS_FILE.exists():
        die("Brak .artifacts/tool-ids.json — najpierw sync_tool.py")
    tool_ids = list(json.loads(TOOL_IDS_FILE.read_text(encoding="utf-8")).values())

    agent = list_agents()[0]
    agent_id = agent["agent_id"]
    branch = next(
        (b for b in list_branches(agent_id) if b.get("name") == branch_name), None
    )
    if not branch:
        die(f"Nie znaleziono brancha {branch_name!r}.")
    branch_id = branch["id"]

    print(f"\n{BOLD('Agent:')} {agent.get('name')}")
    print(f"{BOLD('Branch:')} {branch_name} {DIM(branch_id)}")
    print(f"{BOLD('Toole:')} {', '.join(tool_ids)}")

    # Partial patch: wysyłamy tylko to pole, reszta configu zostaje nietknięta.
    patch = {
        "conversation_config": {
            "agent": {
                "prompt": {
                    "tool_ids": tool_ids,
                }
            }
        }
    }
    el("agents", "update", "--agent-id", agent_id, "--branch-id", branch_id, body=patch)

    print(GREEN("\n✓ Tool podpięty i drafty opublikowane."))

    after = el(
        "agents", "procedures", "list", "--agent-id", agent_id, "--branch-id", branch_id
    )
    for proc in after.get("procedures", []):
        state = (
            YELLOW("draft")
            if proc.get("has_draft")
            else GREEN(f"v={proc.get('version_id')}")
        )
        print(f"  {proc.get('name')}: {state}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
