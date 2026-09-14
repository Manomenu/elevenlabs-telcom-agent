#!/usr/bin/env python3
"""Listuje agentów ElevenLabs wraz z ich branchami."""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from el_common import BOLD, DIM, fmt_branch, list_agents, list_branches


def main() -> int:
    as_json = "--json" in sys.argv[1:]
    agents = list_agents()

    if as_json:
        for a in agents:
            a["branches"] = list_branches(a["agent_id"])
        print(json.dumps(agents, indent=2, ensure_ascii=False))
        return 0

    if not agents:
        print("Brak agentów na koncie.")
        return 0

    print(f"\nAgenci: {len(agents)}\n")
    for a in agents:
        print(BOLD(a.get("name", "(bez nazwy)")))
        print(f"  {DIM(a['agent_id'])}")
        for b in list_branches(a["agent_id"]):
            print(f"    {fmt_branch(b)}")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
