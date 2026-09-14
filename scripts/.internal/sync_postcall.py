#!/usr/bin/env python3
"""Rejestruje webhook register-call w workspace i podpina go jako post-call
na wskazanym branchu agenta.

Webhooki workspace są globalne (jak toole); branch-scoped jest dopiero
platform_settings.workspace_overrides.webhooks.post_call_webhook_id.
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
NGROK_URL_FILE = ROOT / ".artifacts" / "ngrok-url.txt"
WEBHOOK_NAME = "register-call"


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

    if not NGROK_URL_FILE.exists():
        die("Brak .artifacts/ngrok-url.txt — najpierw ./scripts/infra/up.sh")
    url = NGROK_URL_FILE.read_text(encoding="utf-8").strip().rstrip("/")
    callback = f"{url}/register-call"

    existing = el("webhooks", "list").get("webhooks", [])
    hook = next((w for w in existing if w.get("name") == WEBHOOK_NAME), None)

    # auth_type jest stałą "hmac" — jedyna wartość, jaką przyjmuje schemat.
    settings = {
        "settings": {
            "auth_type": "hmac",
            "name": WEBHOOK_NAME,
            "webhook_url": callback,
        }
    }

    if hook and hook.get("webhook_url") == callback:
        webhook_id = hook.get("webhook_id") or hook.get("id")
        print(f"{DIM('Webhook aktualny')} ({webhook_id}) — bez zmian")
    elif hook:
        # PATCH /v1/workspace/webhooks/{id} nie przyjmuje webhook_url — adresu
        # istniejącego webhooka nie da się zmienić. Adres ngroka zmienia się
        # przy każdym restarcie tunelu, więc jedyne wyjście to odtworzenie.
        stale_id = hook.get("webhook_id") or hook.get("id")
        print(f"{DIM('Webhook ma nieaktualny URL')} ({hook.get('webhook_url')})")
        print(
            f"{DIM('Usuwam i tworzę na nowo')} — URL-a nie da się zmienić przez PATCH"
        )
        el("webhooks", "delete", "--webhook-id", stale_id)
        created = el("webhooks", "create", body=settings)
        webhook_id = created.get("webhook_id") or created.get("id")
    else:
        print(f"{DIM('Tworzę webhook')} {WEBHOOK_NAME}")
        # Tworzenie webhooka workspace wymaga uprawnienia webhooks_write na
        # kluczu API. Odczyt działa bez niego, więc brak uprawnienia ujawnia
        # się dopiero tutaj — wyjaśnij to zamiast pokazywać surowe 401.
        try:
            created = el("webhooks", "create", body=settings)
        except SystemExit:
            print(
                YELLOW(
                    "\n! Klucz API nie ma uprawnienia 'webhooks_write'.\n"
                    "  Dodaj je kluczowi w dashboardzie ElevenLabs\n"
                    "  (Profile → API Keys → edytuj klucz → Webhooks: write),\n"
                    f"  albo utwórz webhook ręcznie z URL:\n    {callback}\n"
                    "  i uruchom ten skrypt ponownie."
                )
            )
            raise
        webhook_id = created.get("webhook_id") or created.get("id")

    if not webhook_id:
        die("Nie udało się ustalić ID webhooka.")

    agent = list_agents()[0]
    agent_id = agent["agent_id"]
    branch = next(
        (b for b in list_branches(agent_id) if b.get("name") == branch_name), None
    )
    if not branch:
        die(f"Nie znaleziono brancha {branch_name!r}.")

    print(f"\n{BOLD('Callback:')} {callback}")
    print(f"{BOLD('Branch:')} {branch_name}")

    patch = {
        "platform_settings": {
            "workspace_overrides": {
                "webhooks": {
                    "post_call_webhook_id": webhook_id,
                }
            }
        }
    }
    el(
        "agents",
        "update",
        "--agent-id",
        agent_id,
        "--branch-id",
        branch["id"],
        body=patch,
    )

    print(GREEN(f"\n✓ post_call_webhook_id = {webhook_id}"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
