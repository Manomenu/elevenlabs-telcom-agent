# ElevenLabs — narzędzia do podpięcia pod Claude Code

Zebrane i zweryfikowane materiały: oficjalny plugin (skills + MCP), repo skilli, hosted MCP server, docs MCP, konwencje `llms.txt` oraz CLI (agents-as-code).

---

## 1. Oficjalny plugin — `elevenlabs/plugin`

Repo: <https://github.com/elevenlabs/plugin> — *"Plug in for Coding Agents"*. Działa z **Claude Code**, **Cursor** i **OpenAI Codex**.

### Instalacja w Claude Code

```
/plugin marketplace add elevenlabs/plugin
/plugin install elevenlabs@elevenlabs
```

Dev / lokalnie:

```bash
claude --plugin-dir /path/to/plugin
```

Codex:

```
codex plugin marketplace add elevenlabs/plugin
```

W Cursorze: z [Cursor marketplace](https://cursor.com/marketplace) albo przez dodanie repo jako plugin. Przy pierwszym połączeniu z MCP trzeba przejść OAuth kontem ElevenLabs.

### Struktura repo

```
.claude-plugin/   marketplace.json, plugin.json
.codex-plugin/
.cursor-plugin/
architect/        skills + reference + commands
skills/           general/ + mcp/
mcp.json          konfiguracja hosted MCP
server.json
```

Skille żyją w trzech drzewach:

| Drzewo | Co to |
|---|---|
| `skills/general/` | produktowe skille ElevenLabs, kopiowane z upstream [`elevenlabs/skills`](https://github.com/elevenlabs/skills) — **nie edytować tutaj**, kontrybuować do upstreamu |
| `skills/mcp/` | plugin-native skille uczące agenta obsługi dołączonego MCP servera |
| `architect/skills/` | Architect — opiniowane workflow do budowy i iterowania agentów ElevenLabs (mirror wewnętrznego plugina Architect); wspólne przykłady payloadów w `architect/reference/` |

---

## 2. Skille produktowe (`skills/general/`, 10 szt.)

| Skill | Opis |
|---|---|
| `agents` | Budowa real-time voice AI agents i asystentów |
| `dubbing` | Dubbing audio/wideo na inne języki z zachowaniem głosów oryginalnych mówców |
| `music` | Generowanie utworów instrumentalnych, piosenek z tekstem, muzyki tła i jingli |
| `setup-api-key` | Przeprowadzenie użytkownika przez konfigurację klucza API ElevenLabs |
| `sound-effects` | Generowanie efektów dźwiękowych i tekstur audio z opisu tekstowego |
| `speech-engine` | Dodanie real-time voice conversations do własnego agent runtime |
| `speech-to-text` | Transkrypcja audio do tekstu (Scribe v2) |
| `text-to-speech` | Zamiana tekstu na naturalną mowę w 70+ językach |
| `voice-changer` | Zamiana nagrania na inny głos z zachowaniem emocji i timingu |
| `voice-isolator` | Usuwanie tła i izolacja mowy z audio |

Skill `agents` ma katalog `references/` z konkretami:

- `agent-configuration.md`
- `client-tools.md`
- `installation.md`
- `outbound-calls.md`
- `using-procedure-api.md`
- `widget-embedding.md`
- `writing-procedures.md`

---

## 3. Skille MCP (`skills/mcp/`)

| Skill | Opis |
|---|---|
| `agents-platform` | Tworzenie, konfiguracja, testowanie i deploy voice agents przez dołączony MCP server |
| `creative-studio` | Generowanie mowy, obrazów i wideo oraz transkrypcja audio przez dołączony MCP server |

---

## 4. Architect (`architect/skills/`, 30 szt.)

To jest realna wartość, jeśli budujesz agenta produkcyjnie, a nie tylko czytasz docsy.

| Skill | Opis |
|---|---|
| `agent-simplification` | Uproszczenie złożonego workflow agenta do lżejszej architektury, z równoważnością potwierdzoną test suitem |
| `architect-agent-memory` | Trwałe, branch-scoped zapisywanie faktów, które agent ma pamiętać |
| `architect-branches-versions-merge` | Praca z branchami, wersjami, draftami, traffic splitami i merge'ami agenta |
| `architect-create-client-tool` | Dodanie client tool działającego w przeglądarce / aplikacji / SDK rozmówcy |
| `architect-create-llm-test` | Single-turn test sprawdzający, co agent mówi |
| `architect-create-simulation-test` | Multi-turn test, w którym symulowany user rozmawia z agentem |
| `architect-create-tool-test` | Test asercji, że agent wywołuje (lub nie wywołuje) konkretny tool |
| `architect-create-webhook-tool` | Dodanie agentowi webhook toola wołającego zewnętrzne API |
| `architect-edit-existing-tool` | Bezpieczna zmiana istniejącego toola agenta |
| `architect-edit-string-fields` | Edycja długich pól tekstowych (np. system prompt) bez rozwalania reszty |
| `architect-edit-workflows` | Budowa/zmiana grafu workflow agenta |
| `architect-explain-test-runs` | Wyjaśnienie, dlaczego test lub test run przeszedł/nie przeszedł |
| `architect-explore-agent` | Zmapowanie aktualnego setupu agenta przed wprowadzaniem zmian |
| `architect-generate-agent` | Wygenerowanie nowego agenta z opisu |
| `architect-get-agent-ci-green` | Doprowadzenie czerwonego test suite'a agenta do zieleni |
| `architect-llm-selection` | Wybór właściwego LLM-a dla agenta |
| `architect-manage-procedures` | Dodawanie, edycja, zmiana nazw i inspekcja procedur agenta |
| `architect-migrate-from-competitor` | Migracja voice agenta z Retell, Vapi lub Bland |
| `architect-migrate-to-procedures` | Przejście z agenta sterowanego system promptem na setup oparty o procedury |
| `architect-mock-all-tools` | Zamockowanie wszystkich tool calls, żeby testy symulacyjne były deterministyczne |
| `architect-post-call-data` | Konfiguracja post-call data collection i evaluation criteria |
| `architect-review-live-calls` | Przegląd ostatnich produkcyjnych rozmów i routing wniosków |
| `architect-schedule-launch` | Przygotowanie zmiany na branchu i wstrzymanie merge'a do momentu go-live |
| `architect-secure-for-production` | Doprowadzenie agenta do stanu bezpiecznego i production-ready |
| `architect-structured-procedures` | Pisanie ustrukturyzowanych, deterministycznych procedur |
| `architect-troubleshoot-tool-errors` | Diagnoza źle działającego toola na podstawie dokładnego błędu |
| `architect-turn-taking-latency` | Tuning turn takingu i latencji odpowiedzi agenta |
| `architect-update-config-safely` | Zmiana ustawień agenta bezpiecznymi partial patchami |
| `code-tools` | Generowanie modułów JavaScript/TypeScript dla ElevenLabs code tools |
| `fix-agent-qa-ticket` | Naprawa ticketa z QA triage end-to-end, z weryfikacją i w obrębie brancha |

### Komenda

Architect dostarcza też jedną komendę:

```
/thermo-nuclear-agent-triage-burndown
```

Przepala całą kolejkę conversation-triage danego agenta: klastruje tickety po root cause, naprawia każdy klaster, a potem komentuje i zamyka każdy ticket.

---

## 5. Repo skilli — `elevenlabs/skills`

Repo: <https://github.com/elevenlabs/skills> — *"Collections of skills for building with ElevenLabs"*. Skille zgodne ze [specyfikacją Agent Skills](https://agentskills.io/specification), działają z dowolnym kompatybilnym asystentem.

Instalacja **samych skilli**, bez plugina i MCP:

```bash
npx skills add elevenlabs/skills
```

Wariant z jawnym wskazaniem agenta:

```bash
npx -y skills add elevenlabs/skills --agent claude-code
```

Konfiguracja — wszystkie skille wymagają klucza API:

```bash
export ELEVENLABS_API_KEY="your-api-key"
```

Klucz: [dashboard ElevenLabs](https://elevenlabs.io/app/settings/api-keys) albo przez skill `setup-api-key`.

Repo zawiera też katalog `evals/` z trigger- i functional-evalami dla wszystkich skilli:

```bash
python3 evals/run_all.py -v                 # wszystkie
python3 evals/run_all.py --trigger-only -v  # tylko trigger evals (~3 min)
```

---

## 6. Hosted MCP server

Hostowany po stronie ElevenLabs — **nic nie instalujesz lokalnie, nie wklejasz API key**. Uwierzytelnienie przez OAuth kontem ElevenLabs, ze scoped access do wybranego workspace'u. Dokumentacja: <https://elevenlabs.io/docs/eleven-agents/operate/hosted-mcp>.

### URL-e per region

| Region | URL |
|---|---|
| Global (default) | `https://api.elevenlabs.io/v1/mcp` |
| EU | `https://api.eu.residency.elevenlabs.io/v1/mcp` |
| India | `https://api.in.residency.elevenlabs.io/v1/mcp` |
| Singapore | `https://api.sg.residency.elevenlabs.io/v1/mcp` |

### Konfiguracja z `mcp.json` w pluginie

```json
{
  "mcpServers": {
    "elevenlabs": {
      "url": "https://api.us.elevenlabs.io/v1/mcp",
      "auth": {
        "CLIENT_ID": "0d057191-f2bd-4516-89f8-997e7bfe6bc6",
        "scopes": [
          "convai_read",
          "convai_write",
          "text_to_speech",
          "speech_history_read",
          "flows",
          "image_video_generation",
          "voice_generation"
        ]
      }
    }
  }
}
```

### Co potrafi

- tworzenie agentów z opisu ("create new agents by describing what you want")
- update ustawień: system prompt, głos, język
- listowanie i inspekcja konfiguracji agentów
- przegląd rozmów wraz z transkryptami
- estymacja kosztów LLM
- inspekcja widget config, linków i rozmiaru knowledge base
- duplikowanie i usuwanie agentów
- generowanie próbek mowy (TTS)

### ⚠️ Bezpieczeństwo

- **Usunięcie agenta jest destrukcyjne.** Przeglądaj tool calls przed zatwierdzeniem.
- Ograniczaj write access — jeśli chcesz bezpiecznie, zostaw tylko `convai_read` i rób zmiany przez CLI (wersjonowane w gicie).
- Kontrola jest dwuwarstwowa: uprawnienia OAuth po stronie ElevenLabs + per-tool kontrola w kliencie.
- Administratorzy mogą wyłączyć narzędzia organization-wide.

---

## 7. Docs MCP + konwencje `llms.txt`

### Docs MCP server

Dedykowany serwer do przeszukiwania dokumentacji i API reference:

```
https://elevenlabs.io/_mcp/server
```

Dodanie do Claude Code:

```bash
claude mcp add --transport http elevenlabs-docs https://elevenlabs.io/_mcp/server
```

### Konwencje dokumentacji dla agentów

Z `https://elevenlabs.io/docs/llms.txt`, sekcja *Instructions for AI Agents*:

| Co | Jak |
|---|---|
| Czysty Markdown dowolnej strony | dopisz `.md` do URL-a strony |
| Indeks konkretnej sekcji | dopisz `/llms.txt` do URL-a sekcji |
| Pełny indeks dokumentacji | <https://elevenlabs.io/docs/llms.txt> (~1330 linii) |
| Cała dokumentacja w jednym pliku | <https://elevenlabs.io/docs/llms-full.txt> |
| Integracja z klientem AI | MCP pod `https://elevenlabs.io/_mcp/server` |

**Dobra praktyka:** nie ładuj `llms-full.txt` do kontekstu. Wrzuć indeks/regułę do `CLAUDE.md` w stylu „dociągaj `<url>.md` dla konkretnej strony" i pozwól agentowi pobierać punktowo.

---

## 8. CLI — agent jako kod

Oficjalne CLI: <https://github.com/elevenlabs/cli>, docs: <https://elevenlabs.io/docs/eleven-agents/operate/cli>.

```bash
npm install -g @elevenlabs/cli
# albo
brew install elevenlabs/tap/elevenlabs

elevenlabs auth login
```

CLI czyta `ELEVENLABS_API_KEY` automatycznie i opakowuje REST API.

**Po co:** trzyma agentów jako lokalne pliki konfiguracyjne → agenci jako kod w version control, diff w gicie, CI/CD do automatycznego deployu. Claude Code edytuje pliki, a nie klika w dashboardzie.

ElevenLabs Agents można zarządzać na cztery sposoby: dashboard ElevenAgents, API, Agents CLI, hosted MCP server.

### ⚠️ Deprecated — nie używać

| Pakiet | Status |
|---|---|
| `@elevenlabs/convai-cli` | deprecated → migracja na `@elevenlabs/cli` |
| `@elevenlabs/agents-cli` | deprecated → migracja na `@elevenlabs/cli` |
| `elevenlabs` (npm, JS) | przestarzały pakiet v1.x — **nie instalować** |

Poprawne SDK:

```bash
pip install elevenlabs                  # Python
npm install @elevenlabs/elevenlabs-js   # JavaScript / TypeScript
```

---

## 9. Rekomendowany setup dla tego repo

Katalog `elevenlabs-agents-explore` jest pusty i nie jest repo gitowym. Sensowny start:

```bash
cd /home/maniumek/repos/elevenlabs-agents-explore

# 1. wersjonowanie
git init

# 2. plugin (skills + hosted MCP) — w sesji Claude Code
#    /plugin marketplace add elevenlabs/plugin
#    /plugin install elevenlabs@elevenlabs

# 3. docs MCP do API reference
claude mcp add --transport http elevenlabs-docs https://elevenlabs.io/_mcp/server

# 4. CLI — agent jako kod
npm install -g @elevenlabs/cli
elevenlabs auth login
```

Zasady na start:

1. **MCP do odczytu i inspekcji** (rozmowy, transkrypty, konfiguracja, koszty LLM) — jeśli chcesz bezpiecznie, ogranicz do `convai_read`.
2. **Zmiany przez CLI**, żeby wszystko szło przez pliki i git diff, a nie przez nieodwracalne tool calls.
3. **`CLAUDE.md`** z regułą: dokumentację dociągaj przez `.md`/`llms.txt`, nigdy nie ładuj `llms-full.txt` w całości.
4. Do realnej budowy agenta sięgaj po skille `architect/` — zwłaszcza `architect-explore-agent` (przed zmianami), `architect-update-config-safely`, `architect-create-simulation-test`, `architect-secure-for-production`.

---

## Źródła

- [elevenlabs/plugin (GitHub)](https://github.com/elevenlabs/plugin)
- [elevenlabs/skills (GitHub)](https://github.com/elevenlabs/skills)
- [elevenlabs/cli (GitHub)](https://github.com/elevenlabs/cli)
- [Hosted MCP server — dokumentacja](https://elevenlabs.io/docs/eleven-agents/operate/hosted-mcp)
- [ElevenLabs CLI — dokumentacja](https://elevenlabs.io/docs/eleven-agents/operate/cli)
- [ElevenAgents — overview](https://elevenlabs.io/docs/eleven-agents/overview)
- [Dokumentacja — llms.txt](https://elevenlabs.io/docs/llms.txt)
- [Dokumentacja — llms-full.txt](https://elevenlabs.io/docs/llms-full.txt)
- [ElevenLabs Agent Skills (blog)](https://elevenlabs.io/blog/elevenlabs-agent-skills)
- [Introducing the ElevenLabs Hosted MCP, available in Claude (blog)](https://elevenlabs.io/blog/elevenlabs-mcp-in-claude)
- [Agent Skills — specyfikacja](https://agentskills.io/specification)
