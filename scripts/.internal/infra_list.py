#!/usr/bin/env python3
"""Pokazuje, co stoi z infrastruktury projektu: stan, porty i linki.

Serwisy i porty czytane są z `docker compose ps`, nie z listy w kodzie —
zmiana w docker-compose.yml nie wymaga wtedy ruszania tego skryptu.
"""

import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from el_common import BOLD, CYAN, DIM, GREEN, RED, YELLOW

ROOT = Path(__file__).resolve().parents[2]
NGROK_URL_FILE = ROOT / ".artifacts" / "ngrok-url.txt"

# Ścieżki warte pokazania per serwis: (ścieżka, etykieta).
# Puste dla serwisów, które nie mają nic sensownego pod przeglądarką.
USEFUL_PATHS = {
    "webhook-backend": [("/docs", "OpenAPI / Swagger"), ("/health", "health")],
    "ngrok": [("/", "inspektor requestów")],
}


def compose_ps() -> list[dict]:
    """Stan serwisów. `--format json` daje jeden obiekt na linię (NDJSON)."""
    r = subprocess.run(
        ["docker", "compose", "ps", "--all", "--format", "json"],
        capture_output=True,
        text=True,
        cwd=ROOT,
        encoding="utf-8",
        errors="replace",
    )
    if r.returncode != 0:
        return []
    services = []
    for line in r.stdout.splitlines():
        line = line.strip()
        if line:
            services.append(json.loads(line))
    return services


def published_port(service: dict) -> int | None:
    """Port na hoście. Compose podaje IPv4 i IPv6 osobno — bierzemy pierwszy."""
    for pub in service.get("Publishers") or []:
        if pub.get("PublishedPort"):
            return pub["PublishedPort"]
    return None


def probe(url: str, timeout: float = 2.0) -> int | None:
    """Kod HTTP albo None. Przekierowanie to też żywa odpowiedź, nie błąd."""
    request = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status
    except urllib.error.HTTPError as err:
        return err.code
    except Exception:
        return None


def state_badge(service: dict) -> str:
    state = service.get("State", "?")
    health = service.get("Health") or ""
    if state == "running" and health == "healthy":
        return GREEN("● healthy")
    if state == "running" and health in ("starting", ""):
        return GREEN("● running") if not health else YELLOW("◐ starting")
    if state == "running":
        return YELLOW(f"◐ {health}")
    return RED(f"○ {state}")


def main() -> int:
    if not shutil.which("docker"):
        print(RED("Brak dockera w PATH."))
        return 1

    services = compose_ps()

    print(f"\n{BOLD('Infrastruktura projektu')}")

    if not services:
        print(f"\n  {DIM('Nic nie stoi.')} Start: {CYAN('./scripts/infra/up.sh')}\n")
        return 0

    for service in sorted(services, key=lambda s: s.get("Service", "")):
        name = service.get("Service", "?")
        port = published_port(service)
        running = service.get("State") == "running"

        print(f"\n  {BOLD(name)}  {state_badge(service)}")
        if service.get("Image"):
            print(f"    {DIM('obraz  ')} {service['Image']}")
        if port:
            print(f"    {DIM('port   ')} {port}")

        if not (running and port):
            continue

        for path, label in USEFUL_PATHS.get(name, []):
            url = f"http://localhost:{port}{path}"
            code = probe(url)
            if code is None:
                mark = RED("—")
            elif code < 400:
                mark = GREEN(str(code))
            else:
                mark = YELLOW(str(code))
            print(f"    {DIM(label.ljust(18))} {CYAN(url)}  {mark}")

    # Publiczny adres istnieje niezależnie od pojedynczego serwisu — to on
    # jest tym, co wpisuje się w konfiguracji toola po stronie ElevenLabs.
    if NGROK_URL_FILE.exists():
        public = NGROK_URL_FILE.read_text(encoding="utf-8").strip()
        print(f"\n  {BOLD('Publiczny adres (ngrok)')}")
        print(f"    {CYAN(public)}")
        for path in ("/check-if-serviceable", "/register-call"):
            print(f"    {DIM(path.ljust(24))} {DIM(public + path)}")

    log = ROOT / ".artifacts" / "agent.log"
    if log.exists():
        lines = sum(1 for _ in log.open(encoding="utf-8"))
        print(f"\n  {DIM('log')} .artifacts/agent.log  {DIM(f'({lines} zdarzeń)')}")

    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
