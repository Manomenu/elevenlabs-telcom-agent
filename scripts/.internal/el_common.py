"""Wspólne funkcje dla skryptów ElevenLabs w scripts/.

Trzymane osobno od .sh, żeby nie escapować Pythona w heredocach.
"""

import io
import json
import shutil
import subprocess
import sys
from typing import NoReturn

# Windows domyślnie koduje stdout jako cp1252 — Unicode (strzałki, ✓, polskie
# znaki) wywala skrypt UnicodeEncodeError. Wymuszamy UTF-8 z podmianą znaków.
# isinstance zamiast hasattr: reconfigure() istnieje na TextIOWrapper, a nie na
# TextIO, którym typowane jest sys.stdout — i pod pytest bywa nim naprawdę.
for _stream in (sys.stdout, sys.stderr):
    if isinstance(_stream, io.TextIOWrapper):
        _stream.reconfigure(encoding="utf-8", errors="replace")

# Kolory tylko gdy piszemy na terminal — w pipe czysty tekst.
_TTY = sys.stdout.isatty()


def c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _TTY else text


def BOLD(s: str) -> str:
    return c("1", s)


def DIM(s: str) -> str:
    return c("90", s)


def GREEN(s: str) -> str:
    return c("32", s)


def YELLOW(s: str) -> str:
    return c("33", s)


def RED(s: str) -> str:
    return c("31", s)


def CYAN(s: str) -> str:
    return c("36", s)


def die(msg: str, code: int = 1) -> NoReturn:
    """Kończy proces błędem.

    NoReturn jest istotne dla analizatorów: bez niego po `if not x: die(...)`
    nadal widzą x jako Optional i zgłaszają fałszywe "None is not subscriptable".
    """
    print(RED(f"✗ {msg}"), file=sys.stderr)
    sys.exit(code)


def elevenlabs_bin() -> str:
    """Pełna ścieżka do CLI.

    Na Windows 'elevenlabs' to .cmd/.ps1, a nie .exe — subprocess bez
    rozwiniętej ścieżki rzuca WinError 2.
    """
    path = shutil.which("elevenlabs")
    if not path:
        die("Brak 'elevenlabs' w PATH. npm install -g @elevenlabs/cli")
    return path


def el(*args: str) -> dict:
    """Wywołuje elevenlabs CLI z --format json i zwraca sparsowany wynik."""
    cmd = [elevenlabs_bin(), *args, "--format", "json"]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        die(f"{' '.join(cmd)}\n{(r.stderr or r.stdout).strip()}")
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        die(f"Niepoprawny JSON z: {' '.join(cmd)}\n{r.stdout[:400]}")


def list_agents() -> list:
    d = el("agents", "list")
    return d.get("agents", d if isinstance(d, list) else [])


def list_branches(agent_id: str) -> list:
    d = el("agents", "branches", "list", "--agent-id", agent_id)
    branches = d.get("results", [])
    # Main (bez rodzica) najpierw, potem alfabetycznie.
    branches.sort(
        key=lambda b: (b.get("parent_branch_id") is not None, b.get("name", ""))
    )
    return branches


def fmt_branch(b: dict) -> str:
    """Jedna linia opisu brancha — używane i przy listowaniu, i przy wyborze."""
    live = b.get("current_live_percentage", 0) or 0
    pct = GREEN(f"{live:>5.1f}%") if live > 0 else DIM(f"{live:>5.1f}%")
    flags = ""
    if b.get("draft_exists"):
        flags += " " + YELLOW("DRAFT")
    if b.get("is_archived"):
        flags += " " + DIM("(archived)")
    return (
        f"{b.get('name', ''):<14} {pct}  {DIM(b.get('id', ''))}"
        f"  calls7d={b.get('calls_7d', 0)}{flags}"
    )


def pick(items: list, label, prompt: str):
    """Interaktywny wybór z listy. Zwraca wybrany element.

    Przy jednym elemencie wybiera go automatycznie — nie ma czego wybierać.
    """
    if not items:
        die("Brak elementów do wyboru.")

    if len(items) == 1:
        print(f"{DIM('→ jedyna opcja:')} {label(items[0])}")
        return items[0]

    for i, it in enumerate(items, 1):
        print(f"  {CYAN(str(i).rjust(2))}) {label(it)}")

    while True:
        try:
            raw = input(f"\n{prompt} [1-{len(items)}, q=wyjście]: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            die("Przerwano.", 130)
        if raw.lower() in ("q", "quit", "exit"):
            die("Przerwano.", 130)
        if raw.isdigit() and 1 <= int(raw) <= len(items):
            return items[int(raw) - 1]
        print(RED(f"  Podaj liczbę 1-{len(items)} albo q."))
