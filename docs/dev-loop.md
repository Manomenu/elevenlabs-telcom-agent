# Dev loop — ElevenLabs Agents jako kod

Jak pracujemy w tym repo. Stan na **2026-09-11**, CLI `@elevenlabs/cli` **1.2.0**.

---

## 0. Model mentalny — gdzie żyje agent

**Agent nie jest naszym kodem.** Jest obiektem konfiguracyjnym na serwerach ElevenLabs (~60+ pól JSON: ASR, turn-taking, TTS, prompt, LLM, toole, workflow).

Mamy **jeden obiekt i dwa edytory**:

| Edytor | Do czego |
|---|---|
| Dashboard ElevenLabs (drag & drop, panel) | szybka eksploracja, rysowanie workflow |
| Repo + CLI (`push`/`pull`) | wersjonowanie, review, CI |

`pull` / `push` to most między nimi. Repo trzyma **kopię** obiektu jako pliki.

⚠️ **To nie jest git.** Nie ma merge'a plików ani wykrywania konfliktów. Zmiana tego samego pola w dashboardzie i w pliku → `push` nadpisze dashboard, `pull` nadpisze plik. **Po cichu.** Stąd zasada kierunku w §4.

**SDK nie używamy.** Agent stoi u nich. Piszemy tylko konfigurację (JSON) i — docelowo — backend webhook tooli.

---

## 1. Stan repo

```
agents.json                      ← rejestr: agent ↔ pliki ↔ branch_id ↔ version_id
agent_configs/
  Telecommunication-platform-agent.json       ← branch Main
  Telecommunication-platform-agent.dev.json   ← branch dev
tools.json                       ← {"tools": []}  (pusty)
tests.json                       ← {"tests": []}  (pusty)
.env                             ← ELEVENLABS_API_KEY   (w .gitignore!)
```

**Agent:** `Telecommunication platform agent` — `agent_9601m28wb4h1ej18px9j1eqmpbv7`

| Branch | ID | Ruch | Parent |
|---|---|---|---|
| `Main` | `agtbrch_7401m28wb5v3f0g8e80hj5jkb2b0` | 100% | — |
| `dev` | `agtbrch_0401m28xqcy0f7fv667vtmyepts8` | 0% | Main |

Oba `protection_status: writer_perms_required`, `draft_exists: false`.

Konfiguracja dziś: `llm: qwen35-397b-a17b`, `temperature: 0.0`, `language: en`, prompt 4245 znaków, **0 tooli**, **0 testów**, workflow obecny.

---

## 2. Auth — jedno źródło, nigdy dwa

**Był problem:** `error[api]: Only one of xi-api-key and authorization headers must be provided.`

**Przyczyna:** dwa poświadczenia naraz — `ELEVENLABS_API_KEY` w `.env` (CLI czyta go z katalogu projektu) **oraz** OAuth w Windows Credential Manager po `elevenlabs auth login`. CLI wysyłało oba nagłówki, API odrzucało.

**Rozwiązanie: zostajemy przy API key z `.env`, OAuth wylogowany.**

```bash
elevenlabs auth logout      # usuwa wpisy OAuth z keyringu
```

Dlaczego key, a nie OAuth: klucz jest przenośny i działa tak samo w CI (OAuth siedzi w keyringu Windows — w GitHub Actions nie zadziała).

**Diagnostyka, gdyby wróciło:**

```bash
elevenlabs agents list --debug 2>&1 | grep -iE "^> (authorization|xi-api-key)"
```

Ma być **dokładnie jeden** nagłówek. Jak są dwa — `auth logout` albo usuń klucz z `.env`.

⚠️ `.env` **musi** zostać w `.gitignore`. Sprawdzenie: `git check-ignore -v .env`

---

## 3. Pętla dewelopmentu

Dev robimy **na branchu `dev`**, `Main` zostaje nietknięty (ma 100% ruchu).

```bash
# 1. START DNIA — zaciągnij stan z ElevenLabs
elevenlabs agents pull --all --all-branches --yes
git diff                    # co zmieniło się poza repo?
git add -A && git commit -m "pull: stan przed zmianami"

# 2. ZMIANA — edytuj plik brancha dev
#    agent_configs/Telecommunication-platform-agent.dev.json

# 3. WALIDACJA lokalna (bez wysyłki)
elevenlabs agents push --agent agent_9601m28wb4h1ej18px9j1eqmpbv7 --branch dev --dry-run

# 4. WYSYŁKA na dev
elevenlabs agents push --agent agent_9601m28wb4h1ej18px9j1eqmpbv7 \
  --branch dev --version-description "opis zmiany"

# 5. TESTY
elevenlabs agents run_tests --help    # patrz §6

# 6. COMMIT
git add -A && git commit -m "feat(agent): ..."
```

**Po klikaniu w dashboardzie** — zawsze najpierw `pull`, potem `git diff`. Inaczej następny `push` cicho skasuje to, co wyklikałeś.

---

## 4. Zasada kierunku (najważniejsza reguła)

Ponieważ nie ma wykrywania konfliktów, **w danym momencie jeden branch ma jeden kierunek synchronizacji**:

| Tryb | Kierunek | Kiedy |
|---|---|---|
| **Eksploracja** | dashboard → `pull` → repo | rysowanie workflow, szukanie kształtu |
| **Inżynieria** | repo → `push` → dashboard | normalna praca, review, CI |

Nigdy oba naraz na tym samym branchu. Przy przełączaniu trybu: najpierw `pull`, `git diff`, commit — dopiero potem edycja plików.

Dodatkowo: jeśli `draft_exists: true` na branchu, niezacommitowany draft po stronie ElevenLabs **blokuje operacje** i potrafi wywalić `push`. Najpierw zapisz albo odrzuć draft w dashboardzie.

---

## 5. dev → Main

Dwa poziomy wersjonowania: **git** (nasz) i **branche ElevenLabs** (ich). Odwzorowujemy 1:1.

Merge robi się **po stronie ElevenLabs**, nie w gicie:

```
POST /v1/convai/agents/{agent_id}/branches/{source_branch_id}/merge
```

Zasady (z `architect-branches-versions-merge`):

1. **Zawsze merge preview przed merge.** Merge jest **destrukcyjny na targecie** i tworzy nową wersję.
2. Branch merguje się do swojego `parent_branch_id` — `dev` → `Main`. Nie da się do niepowiązanego brancha.
3. **Nie skacz 0 → 100%.** Rampa: 10% → 50% → 100%, analityka między krokami.
4. **Traffic split musi sumować się do dokładnie 100%** na wszystkich aktywnych branchach. Podnosisz dev o 10% → obniżasz Main o 10% w tym samym wywołaniu. Najczęstsza przyczyna błędu walidacji.
5. Tylko aktywne (niezarchiwizowane) branche w splicie.
6. `current_live_percentage` rządzi tylko ruchem **nieprzypiętym**. Branch na 0% **wciąż** dostaje rozmowy, gdy ktoś wskaże go jawnie (`branch_id` w API / pin w kliencie).

**Po merge:** `pull` + commit, żeby repo dogoniło stan.

**HARD GATE:** nigdy nie pisz do `branch_id`, którego przed chwilą nie potwierdziłeś. Nazwa brancha ≠ id. Zawsze najpierw lista branchy, dopasowanie po `name`, dopiero potem zapis.

---

## 6. Testy

`agents simulate_conversation` i `simulate_conversation_stream` są **[DEPRECATED]** — mimo że tutoriale wciąż je pokazują. Idziemy przez:

```bash
elevenlabs agents tests ...        # zarządzanie testami
elevenlabs agents run_tests ...    # uruchomienie na agencie
```

Trzy rodzaje (skille `architect-create-*-test`):

| Typ | Co sprawdza |
|---|---|
| **LLM test** | single-turn — *co agent mówi* |
| **Tool test** | czy agent **wywołał** (lub nie) konkretny tool |
| **Simulation test** | multi-turn — symulowany user rozmawia z agentem |

Do determinizmu: `architect-mock-all-tools` — zamockuj wszystkie tool calls, żeby testy nie biły w prawdziwe API.

---

## 7. Prompt vs procedury

Domyślnie cała logika siedzi w jednym system prompcie (u nas: 4245 znaków). **Kierunek ElevenLabs to procedury** — nazwane jednostki logiki z triggerami, model draft → publish.

Ścieżka (skill `architect-migrate-to-procedures`):

1. `GET /v1/convai/agents/$AGENT_ID?branch_id=$BRANCH_ID` — odczytaj prompt
2. Wytypuj kandydatów: instrukcje krok-po-kroku, logika warunkowa
3. Tabela propozycji: *Name / Trigger / Brief content* → akceptacja
4. `POST .../branches/$BRANCH_ID/procedures` — **po jednej na raz**, potwierdzając każdą
5. Publish draftów: `PATCH /v1/convai/agents/$AGENT_ID?branch_id=$BRANCH_ID`
6. Dopiero potem odchudź system prompt

---

## 8. Autorytet: spec, nie przykłady

`example-agent.json` w pluginie to **katalog pól, nie szablon**. Ich własny README mówi wprost: *„Do not start from one"* — kopiowanie daje maksymalistyczny config, którego nikt nie wybrał.

Prawda żyje w publicznym specu (bez auth, ~1470 schematów):

```bash
curl -s https://api.elevenlabs.io/openapi.json -o /tmp/el-openapi.json
jq -r '.components.schemas["PromptAgentAPIModel-Input"].properties | keys[]' /tmp/el-openapi.json
```

Uwaga na sufiksy **`-Input`** (request) / **`-Output`** (response) — budując payload chcesz `-Input`. Spodziewaj się `$ref` — jedno zapytanie zwykle nie wystarczy.

Alternatywa bez curl: MCP `elevenlabs-docs` (`searchDocs`), podpięty w tym projekcie.

### Trzy pułapki, które ich dokumentacja nazywa „zgadywane błędnie wielokrotnie"

1. **`path_params_schema`** to obiekt kluczowany nazwą parametru. **`query_params_schema`** to `{properties, required}`. Inne kształty — pomyłka daje `Input should be a valid dictionary`.
2. **Property ma dokładnie jedno źródło wartości**, a `description` jest jednym z nich. Zbiór wykluczający: `description`, `dynamic_variable`, `is_system_provided`, `constant_value`, `is_omitted`. Property z `constant_value` **nie może mieć opisu** → `Can only set one of: ...`
3. **Ścieżki odpowiedzi to notacja kropkowa**: `reservation.status`, **nigdy** `$.reservation.status`.

---

## 9. Narzędzia w tym projekcie

| Co | Status |
|---|---|
| `@elevenlabs/cli` 1.2.0 | zainstalowane globalnie |
| Plugin `elevenlabs@elevenlabs` | aktywny, 44 skille (prefiks `elevenlabs:`) |
| MCP `elevenlabs-docs` | `https://elevenlabs.io/docs/_mcp/server` — **z `/docs`** w ścieżce |
| Hosted MCP (z plugina) | OAuth przy pierwszym użyciu — **zostaw `convai_read`**, write idzie przez CLI |

**Deprecated — nie używać:** `@elevenlabs/convai-cli`, `@elevenlabs/agents-cli`, `elevenlabs` (stary npm JS SDK v1.x).
`@elevenlabs/cli` to **cel migracji** z tamtych — ten jest aktualny.

### Skille warte zapamiętania

- `architect-explore-agent` — zmapuj agenta **przed** zmianami
- `architect-update-config-safely` — partial patche
- `architect-structured-procedures` — schemat JSON procedur inline
- `architect-create-webhook-tool` — toole HTTP
- `architect-mock-all-tools` + `architect-get-agent-ci-green` — testy i CI
- `architect-secure-for-production` — przed go-live
- `architect-migrate-from-competitor` — Retell / Vapi / Bland

---

## 10. Skrypty pomocnicze

```
scripts/
  list-agents.sh        # agenci + ich branche
  pull-agent.sh         # interaktywny pull
  .internal/            # helpery pythonowe (nie wołaj bezpośrednio)
    el_common.py
    list_agents.py
    pull_agent.py
```

```bash
./scripts/list-agents.sh           # tabela: nazwa, id, % ruchu, DRAFT, calls7d
./scripts/list-agents.sh --json    # JSON z zagnieżdżonymi branchami

./scripts/pull-agent.sh            # wybór agenta -> wybór brancha -> pull
./scripts/pull-agent.sh --all      # wybór agenta -> wszystkie branche, bez pytania
```

### Dwie pułapki `pull`, które skrypt obchodzi

**1. `pull` bez `--update` cicho nic nie robi.** Agenta obecnego w `agents.json` pomija (`already exists`), kończąc się **kodem 0**. Wygląda na sukces, a config się nie zmienił. Skrypt zawsze dodaje `--update` i ostrzega, gdy CLI zgłosi `0 created, 0 updated`.

**2. `--branch <id>` psuje `agents.json`.** Przekazanie ID brancha rejestruje go pod ID zamiast nazwy — powstaje **drugi wpis** obok istniejącego (`dev` i `agtbrch_...` jako osobne branche), dochodzi duplikat pliku configu, a główny `config` agenta zostaje przestawiony na wersję z tego brancha.

Dlatego skrypt pozwala wybrać brancha (żeby zobaczyć stan: % ruchu, drafty), ale **pull zawsze woła `--all-branches`** — to jedyny tryb, który nazywa branche poprawnie. Ściąga komplet, więc wybrany branch i tak jest zaktualizowany.

Naprawa, gdyby rejestr się rozjechał:

```bash
rm agent_configs/*.agtbrch_*.json
elevenlabs agents pull --all --all-branches --update --yes
# usuń osierocone klucze 'agtbrch_*' z sekcji branches w agents.json
```

---

## 11. Co jest branch-scoped, a co nie

To determinuje, jak pracujesz — i było źródłem niejasności:

| Byt | Branch-scoped? | Jak |
|---|---|---|
| **Procedury** | ✅ TAK | `--agent-id` + `--branch-id` |
| **Toole** | ❌ NIE | workspace-level, wspólne dla wszystkich agentów |
| **Przypisanie toola do agenta** | ✅ TAK | `conversation_config.agent.prompt.tool_ids` |
| **Webhook workspace** | ❌ NIE | globalny |
| **post_call_webhook_id** | ✅ TAK | `platform_settings.workspace_overrides.webhooks` |

Czyli: **tool tworzysz raz, a na branchu decydujesz tylko, czy agent go widzi.** Nie da się mieć innej definicji toola na `dev` niż na `Main`.

---

## 12. Infrastruktura projektu

```
docker-compose.yml        webhook-backend (FastAPI) + ngrok
backend/
  app.py                  /check-if-serviceable, /register-call, /health
  Dockerfile
  requirements.txt
.artifacts/
  agent.log               NDJSON — jedno zdarzenie na linię
  ngrok-url.txt           publiczny adres bieżącego tunelu
  tool-ids.json           nazwa toola → id w ElevenLabs
```

```bash
./scripts/infra/up.sh              # start (kończy się wywołaniem list.sh)
./scripts/infra/up.sh --rebuild    # przebuduj obraz backendu
./scripts/infra/list.sh            # co stoi: stan, porty, linki
./scripts/infra/down.sh            # stop
./scripts/infra/down.sh --clean    # stop + wyczyść log i adres
```

`list.sh` czyta serwisy i porty z `docker compose ps`, nie z listy w kodzie — zmiana w `docker-compose.yml` nie wymaga ruszania skryptu. Sonduje też przydatne ścieżki (`/docs`, `/health`) i pokazuje kod HTTP, więc od razu widać, czy serwis naprawdę odpowiada, a nie tylko „stoi".

### Python: dwa drzewa, jedna konfiguracja lintu

W repo są **dwa niezależne drzewa Pythona**, każde z własnym `pyproject.toml`:

| | `backend/` | `scripts/` |
|---|---|---|
| Co to | usługa HTTP w kontenerze | narzędzia CLI na hoście |
| Zależności | fastapi, uvicorn, pydantic | **żadnych** — czysty stdlib |
| Gdzie działa | Docker | host |
| Uruchamiane przez | `uvicorn app:app` | wrappery `.sh` |

Żaden nie ma `[build-system]` — to usługa i zbiór skryptów, nie biblioteki do zbudowania. `pyproject.toml` służy tam wyłącznie jako deklaracja zależności.

`scripts/` celowo nie ma zależności: z ElevenLabs rozmawia przez CLI (`elevenlabs`, npm), nie przez pythonowe SDK. Dzięki temu działa bez virtualenva.

### uv — backend

```bash
cd backend
uv sync              # venv + instalacja z uv.lock
uv run uvicorn app:app --reload --port 8080   # lokalnie, bez dockera
uv add <pakiet>      # dodanie zależności (aktualizuje lock)
```

**`uv.lock` jest wersjonowany** — to on sprawia, że obraz i lokalny venv mają identyczne wersje. Obraz instaluje przez `uv sync --locked --no-install-project --no-dev`:

- `--locked` — błąd, jeśli lock rozjechał się z `pyproject.toml`, zamiast cichego przeliczenia
- `--no-install-project` — projekt nie jest pakietem do zainstalowania
- `--no-dev` — ruff i httpx nie trafiają do obrazu produkcyjnego

`UV_PROJECT_ENVIRONMENT=/usr/local` instaluje wprost do systemowego Pythona obrazu, więc nie ma zagnieżdżonego venva ani potrzeby aktywacji w `CMD`.

### Kontekst IDE

`backend/.venv` powstaje dopiero po `uv sync` — bez niego edytor zgłasza *„Import fastapi could not be resolved"*. Wskazanie interpretera jest w repo:

| Plik | Do czego |
|---|---|
| `pyrightconfig.json` | interpreter + `extraPaths` dla obu drzew; działa niezależnie od IDE |
| `.vscode/settings.json` | to samo dla VS Code + ruff jako formatter, format i sortowanie importów przy zapisie |

`extraPaths` obejmuje `backend` i `scripts/.internal`, żeby edytor rozumiał importy lokalne (`app`, `el_common`) tak samo jak ruff przez `src`.

W PyCharm/IntelliJ wskaż ręcznie: *Settings → Project → Python Interpreter → Add → Existing → `backend/.venv/Scripts/python.exe`*.

`scripts/` nie ma `pyproject.toml` — nie miałby czego deklarować (zero zależności, nic do zbudowania), a lint i tak bierze `ruff.toml` z korzenia.

**Lint i formatowanie: jeden `ruff.toml` w korzeniu**, wspólny dla obu drzew — ruff szuka konfiguracji w górę drzewa.

### Weryfikacja: `./scripts/test-solution.sh`

```bash
./scripts/test-solution.sh          # sprawdza
./scripts/test-solution.sh --fix    # + autopoprawki i formatowanie
```

Sześć kroków, bez potrzeby stojącej infrastruktury:

| Krok | Co łapie |
|---|---|
| `ruff check` | lint obu drzew |
| `ruff format --check` | rozjechane formatowanie |
| `pyright` | **ten sam silnik co Pylance** — czerwone podkreślenia z edytora |
| JSON + TOML | literówka w configu agenta ujawniłaby się dopiero przy wysyłce |
| `docker compose config` | błąd w compose — zamiast przy starcie kontenera |
| `bash -n` | składnia skryptów |

Kod wyjścia `1`, gdy cokolwiek zawiedzie — nadaje się do CI i do hooka pre-commit. Brakujące narzędzie jest **pomijane z ostrzeżeniem**, nie zgłaszane jako porażka (np. `npx` niedostępny → pyright pominięty).

Uruchamiaj to po zmianach w kodzie i w konfiguracji — `pyright` w CLI odpowiada temu, co edytor pokazuje na czerwono, więc łapie błędy zanim trafią do repo.

`py312`, linia 88, reguły `E,F,I,UP,B,SIM,RUF`. Dwie rzeczy warte uwagi w konfiguracji:

- **`src = ["backend", "scripts/.internal"]`** — bez tego isort bierze `el_common` i `app` za biblioteki zewnętrzne i wrzuca do złej sekcji importów.
- **`E402` wyłączone tylko dla `scripts/.internal/*.py`** — te pliki dopisują swój katalog do `sys.path` przed importem lokalnych modułów, więc import nie może stać na górze. W `backend/` reguła działa normalnie.

`backend/` jest samowystarczalny (własny `Dockerfile`, `pyproject.toml`, `.dockerignore`), więc kontekstem build jest **`./backend`**.

**Dlaczego ngrok:** ElevenLabs woła webhooki z internetu, więc `localhost` im nie wystarczy. Tunel daje publiczny HTTPS.

⚠️ **Adres ngroka zmienia się przy każdym restarcie tunelu.** Dlatego definicja toola w repo trzyma placeholder `https://REPLACED_BY_SCRIPT`, a skrypt podstawia bieżący URL przed wysyłką. **Po każdym `up.sh` uruchom `sync-dev.sh`**, inaczej tool w ElevenLabs wskazuje na martwy adres.

---

## 13. Dwa kierunki synchronizacji

```bash
./scripts/sync-dev.sh     # repo  →  platforma   (wysyłka)
./scripts/pull-dev.sh     # platforma  →  repo   (po pracy w dashboardzie)
```

To są dwie strony tej samej pętli. Zasada kierunku z §4 mówi, że w danym momencie używasz jednego — nie obu naprzemiennie na tym samym branchu bez commita pomiędzy.

### `pull-dev.sh` — zaciąganie zmian z dashboardu

```bash
./scripts/pull-dev.sh          # branch dev
./scripts/pull-dev.sh nazwa    # inny branch
```

Ściąga trzy rzeczy i wypisuje **tylko te pliki, które faktycznie się zmieniły**:

1. konfigurację agenta (`agents pull`)
2. treść procedur → `agent_configs/procedures/`
3. definicje podpiętych tooli → `agent_configs/tools/`

⚠️ **Kroki 2 i 3 są konieczne, bo `elevenlabs agents pull` ich nie obejmuje.** Ściąga on wyłącznie konfigurację agenta; treść procedur i definicje tooli żyją pod osobnymi endpointami. Bez tego zmiana procedury wyklikana w dashboardzie byłaby dla repo **niewidzialna** — a `sync-dev.sh` nadpisałby ją przy następnym przebiegu.

Szczegóły zachowania:

- **URL toola wraca jako placeholder.** Adres ngroka jest tymczasowy, więc plik w repo trzyma `https://REPLACED_BY_SCRIPT` i nie zmienia się przy każdym restarcie tunelu. Round-trip `pull-dev` → `sync-dev` jest przez to stabilny.
- **Pliki zapisywane tylko przy realnej różnicy treści** — inaczej każdy pull przestawiałby mtime i git pokazywałby ruch tam, gdzie nic się nie zmieniło.
- **Procedura usunięta w dashboardzie** jest sygnalizowana ostrzeżeniem (plik zostaje w repo, więc `sync-dev.sh` by ją odtworzył — usuń go ręcznie, jeśli usunięcie było zamierzone).
- **Draft na branchu** daje ostrzeżenie: pull ściąga ostatnią *opublikowaną* wersję, więc niezapisane zmiany z dashboardu nie przyjdą.

---

## 14. Synchronizacja na dev

```bash
./scripts/sync-dev.sh          # wszystko na dev
./scripts/sync-dev.sh nazwa    # inny branch
```

Kroki: tool → procedury → podpięcie + publikacja → post-call webhook → pull. Idempotentne — powtórne uruchomienie aktualizuje, nie duplikuje.

Źródła prawdy w repo:

```
agent_configs/
  tools/check-if-serviceable.json     definicja webhook toola
  procedures/connect-with-agent.json  treść procedury
```

### Post-call webhook

Krok 4 wymaga uprawnienia **`webhooks_write`** na kluczu API. Bez niego `GET /v1/workspace/webhooks` działa (200), ale `POST` zwraca `missing_permissions`. Skrypt to wykrywa, wypisuje instrukcję i **nie przerywa reszty synchronizacji**.

Nadanie: dashboard → Profile → API Keys → edytuj klucz → Webhooks: write.

⚠️ **URL-a istniejącego webhooka nie da się zmienić.** `PATCH /v1/workspace/webhooks/{id}` przyjmuje tylko `name`, `is_disabled`, `events`, `request_headers`, `retry_enabled` — **`webhook_url` nie ma na tej liście**. Ponieważ adres ngroka zmienia się przy każdym restarcie tunelu, skrypt porównuje zapisany URL z bieżącym i przy różnicy **usuwa webhook i tworzy go na nowo**. Nowe ID trafia wtedy do `post_call_webhook_id` na branchu.

### Tool `check_if_serviceable`

Wymóg „(street i zip) albo (street i city i state)" jest wyrażony **deklaratywnie**, nie tylko w opisie:

```json
"required": ["street"],
"required_constraints": {
  "any_of": [
    { "required": ["street", "zip"] },
    { "required": ["street", "city", "state"] }
  ]
}
```

Backend waliduje to drugi raz (pydantic `model_validator`), więc niekompletne wywołanie dostaje 422 zamiast losowego wyniku.

### Pułapka: długi payload na Windows

`--params '<długi JSON>'` kończy się błędem *„The system cannot find the file specified"* — to limit długości linii poleceń, nie brak pliku. Dlatego skrypty wysyłają body przez **stdin**: `--json -`.

---

## 15. Szybka ściąga

```bash
# stan
elevenlabs agents list --format json
elevenlabs agents branches list --agent-id <AGENT_ID> --format json

# sync
elevenlabs agents pull --all --all-branches --yes
elevenlabs agents push --agent <AGENT_ID> --branch dev --dry-run
elevenlabs agents push --agent <AGENT_ID> --branch dev --version-description "..."

# auth
elevenlabs auth status --format json
elevenlabs agents list --debug 2>&1 | grep -iE "^> (authorization|xi-api-key)"
```
