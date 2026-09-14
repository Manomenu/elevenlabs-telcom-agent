#!/usr/bin/env python3
"""Ładuje artykuły do knowledge base ElevenLabs i indeksuje je dla RAG-a.

Trzy etapy na dokument:
  1. create_from_text  — wgranie treści
  2. compute_rag_index — zbudowanie indeksu wektorowego (bez tego RAG go nie widzi)
  3. podpięcie do agenta — prompt.knowledge_base + rag.enabled

Knowledge base jest workspace-level (jak toole), więc dokumenty powstają raz.
Branch-scoped jest dopiero lista knowledge_base w konfiguracji agenta.
"""

import html
import json
import os
import re
import subprocess
import sys
import time
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
ARTICLES = ROOT / "agent_configs" / "knowledge-base" / "articles.json"
KB_IDS_FILE = ROOT / ".artifacts" / "kb-ids.json"

# Ten sam model, który agent ma już ustawiony w rag.embedding_model — indeks
# zbudowany innym modelem nie zostałby użyty przy wyszukiwaniu.
EMBEDDING_MODEL = "e5_mistral_7b_instruct"

# Baza ma być dostępna tylko w tym kroku workflow, nie w całej rozmowie.
TARGET_NODE_LABEL = "Provide Service Information"


def el(*args: str, body: dict | None = None) -> dict:
    cmd = [elevenlabs_bin(), *args, "--format", "json"]
    stdin_data = None
    if body is not None:
        cmd += ["--json", "-"]
        stdin_data = json.dumps(body)
    result = subprocess.run(
        cmd,
        input=stdin_data,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        die(f"{' '.join(args)}\n{(result.stderr or result.stdout).strip()}")
    return json.loads(result.stdout) if result.stdout.strip() else {}


def to_plain_text(markup: str) -> str:
    """Zamienia HTML artykułu na tekst.

    KB przyjmuje czysty tekst — znaczniki trafiłyby do embeddingów jako szum.
    """
    text = re.sub(r"<br\s*/?>", "\n", markup)
    text = re.sub(r"</p>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    # Wcięcia były robione encjami nbsp; zostaw pojedyncze spacje.
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return "\n".join(line.strip() for line in text.splitlines()).strip()


def document_body(article: dict) -> str:
    """Buduje treść dokumentu.

    rag_description i llm_guide idą razem z treścią: pierwsze poprawia trafność
    wyszukiwania, drugie mówi agentowi, jak o tym mówić.
    """
    return "\n\n".join(
        [
            f"# {article['title'].strip()}",
            f"## Summary\n{article['rag_description'].strip()}",
            f"## Content\n{to_plain_text(article['content'])}",
            f"## Guidance for the assistant\n{article['llm_guide'].strip()}",
        ]
    )


def index_document(doc_id: str, attempts: int = 30) -> str:
    """Uruchamia indeksowanie i czeka, aż się skończy.

    Wywołanie jest asynchroniczne i zwraca 'created' natychmiast; powtórzone
    wywołanie na tym samym dokumencie zwraca bieżący stan zamiast zaczynać od
    nowa. Bez czekania skrypt zgłaszałby sukces przy niegotowym indeksie.
    """
    for attempt in range(attempts):
        result = el(
            "agents",
            "knowledge-base",
            "document",
            "compute_rag_index",
            "--documentation-id",
            doc_id,
            "--model",
            EMBEDDING_MODEL,
        )
        status = result.get("status", "?")
        if status in ("succeeded", "failed"):
            return status
        if attempt < attempts - 1:
            time.sleep(2)
    return status


def find_node(agent_config: dict, label: str) -> str:
    """Zwraca id węzła workflow o podanej etykiecie."""
    nodes = agent_config.get("workflow", {}).get("nodes", {})
    for node_id, node in nodes.items():
        if node.get("label") == label:
            return node_id
    available = [n.get("label") for n in nodes.values() if n.get("label")]
    die(f"Nie znaleziono węzła {label!r}. Dostępne: {available}")


def existing_documents() -> dict[str, str]:
    """Mapa nazwa -> id dla dokumentów już obecnych w workspace."""
    listing = el("agents", "knowledge-base", "list")
    found = {}
    for doc in listing.get("documents", []):
        name = doc.get("name")
        doc_id = doc.get("id") or doc.get("documentation_id")
        if name and doc_id:
            found[name] = doc_id
    return found


def main() -> int:
    branch_name = sys.argv[1] if len(sys.argv) > 1 else "dev"

    if not ARTICLES.exists():
        die(f"Brak pliku z artykułami: {ARTICLES}")
    articles = json.loads(ARTICLES.read_text(encoding="utf-8"))

    print(f"\n{BOLD('Knowledge base')} {DIM(f'({len(articles)} artykułów)')}")

    known = existing_documents()
    kb_ids: dict[str, str] = {}

    for article in articles:
        name = article["url_id"]
        if name in known:
            # Treść dokumentu jest niezmienna — podmiana wymaga skasowania
            # i wgrania na nowo, co unieważnia indeks. Przy tym samym pliku
            # nie ma po co.
            print(f"  {DIM('=')} {name} {DIM('— już jest')}")
            kb_ids[name] = known[name]
            continue

        created = el(
            "agents",
            "knowledge-base",
            "documents",
            "create_from_text",
            body={"name": name, "text": document_body(article)},
        )
        doc_id = created.get("id")
        if not doc_id:
            die(f"Nie udało się utworzyć dokumentu {name!r}.")
        print(f"  {GREEN('+')} {name} {DIM(doc_id)}")
        kb_ids[name] = doc_id

    print(f"\n{BOLD('Indeksowanie RAG')} {DIM(EMBEDDING_MODEL)}")
    for name, doc_id in kb_ids.items():
        print(f"  {DIM('…')} {name}", end="", flush=True)
        status = index_document(doc_id)
        mark = GREEN("✓") if status == "succeeded" else YELLOW("!")
        print(f"\r  {mark} {name} {DIM(status)}          ")

    KB_IDS_FILE.parent.mkdir(parents=True, exist_ok=True)
    KB_IDS_FILE.write_text(json.dumps(kb_ids, indent=2), encoding="utf-8")

    # Podpięcie do agenta na branchu: lista dokumentów + włączenie RAG-a.
    agent = list_agents()[0]
    agent_id = agent["agent_id"]
    branch = next(
        (b for b in list_branches(agent_id) if b.get("name") == branch_name), None
    )
    if not branch:
        die(f"Nie znaleziono brancha {branch_name!r}.")

    locators = [
        {"type": "text", "name": name, "id": doc_id, "usage_mode": "auto"}
        for name, doc_id in kb_ids.items()
    ]

    agent_config = el(
        "agents", "get", "--agent-id", agent_id, "--branch-id", branch["id"]
    )
    node_id = find_node(agent_config, TARGET_NODE_LABEL)

    # Węzeł ma `additional_knowledge_base`, więc baza jest widoczna dopiero po
    # wejściu w ten krok workflow. Lista na poziomie agenta zostaje pusta —
    # inaczej dokumenty byłyby dostępne w każdym węźle.
    workflow = {
        key: value
        for key, value in agent_config["workflow"].items()
        # subgraphs jest w odpowiedzi, ale request go nie przyjmuje.
        if key != "subgraphs"
    }
    workflow["nodes"][node_id]["additional_knowledge_base"] = locators

    patch = {
        "conversation_config": {
            "agent": {
                "prompt": {
                    "knowledge_base": [],
                    "rag": {"enabled": True, "embedding_model": EMBEDDING_MODEL},
                }
            }
        },
        "workflow": workflow,
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

    print(f"\n{GREEN('✓')} Podpięte do {CYAN(branch_name)}, RAG włączony")
    print(f"  {DIM('ID zapisane w .artifacts/kb-ids.json')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
