# SuwalkiCable — a voice agent on ElevenLabs Agents

A weekend demo of a voice agent for a fictional cable operator, maintained as
**agent-as-code**: the agent's configuration lives in this repository as files,
and changes reach the platform through the CLI rather than through clicks in the
dashboard.

---

## Why this exists

I build a comparable chatbot professionally — not a platform, but a solution
written entirely in code. That project was started because we needed an agent
capable of running **structured procedures**, and structured procedures are
exactly what ElevenLabs Agents provides. Their product therefore became a
natural point of comparison: it was worth seeing how they solved what we are
building from scratch.

There is a second reason. Voice is a direction I want to understand properly, so
experimenting with this platform had a double justification.

The demo is deliberately small: a handful of representative pieces — a webhook
tool, two kinds of procedure, a knowledge base behind RAG — assembled to the
point where the platform's real behaviour becomes visible, and no further.

**The demo contains no code, prompts, configuration or data from my work.** It
was built outside working hours, against a public API, on an entirely invented
domain.

---

## What it does

A customer-service agent for a cable operator, with three workflow steps:
greeting, providing service information, and closing the conversation.

| Element | Implementation |
|---|---|
| **Free-form procedure** | `connect-with-agent` — greeting, echoing the message, handing off |
| **Deterministic procedure** | `self-router-health-check` — router diagnostics, branching on the status light |
| **Webhook tool** | `check_if_serviceable` — service availability at an address |
| **Knowledge base + RAG** | 6 articles, scoped to the *Provide Service Information* node |
| **Post-call webhook** | `register-call` — records a finished conversation to the log |
| **Backend** | FastAPI in a container, ngrok tunnel, NDJSON log |

Model: `qwen35-397b-a17b`, temperature 0.0.

### Quick start

```bash
cp .env.example .env          # fill in ELEVENLABS_API_KEY and NGROK_AUTHTOKEN
./scripts/infra/up.sh         # backend + tunnel, prints the public address
./scripts/sync-dev.sh         # repo → platform (dev branch)
./scripts/kb/seed.sh          # knowledge base + RAG index
```

Full documentation of the working loop: [`docs/dev-loop.md`](docs/dev-loop.md).

---

## Architectural decisions

### The repository is the source of truth, not the dashboard

An agent on the platform is a configuration object reachable two ways: the
dashboard and the CLI. I chose the CLI and files, because only then does every
change produce a diff and become reviewable.

One consequence had to be handled explicitly: **there is no conflict detection
in either direction**. `agents push` reports `Will push (force override)` and
overwrites whatever is on the platform, regardless of whether the remote version
is newer; `agents pull --update` is documented as overriding local
configurations with remote changes. Neither warns, because overwriting is the
intended behaviour rather than an edge case.

Hence an explicit rule about direction, and two separate scripts rather than one
"synchronise":

- `sync-dev.sh` — repo → platform
- `pull-dev.sh` — platform → repo

At any given moment you use one of them, not both alternately.

### Writes go through the CLI only; MCP stays read-only

The hosted MCP server can create, update and delete agents, and ElevenLabs
flags deletion as destructive in its own documentation. It offers two layers of
control for this — OAuth scopes and per-tool approval in the MCP client — so the
risk is manageable rather than alarming.

The reason to keep writes on one channel is different: a change made through MCP
leaves nothing behind in the repository. Restricting writes to the CLI is what
keeps the files an honest record of the agent, rather than a document that
happens to agree with it.

### `pull-dev` fetches more than `agents pull`

The built-in `pull` covers **only the agent configuration**. Procedure contents
and tool definitions live behind separate endpoints, so a procedure edited in
the dashboard would be invisible to the repository, and the next `sync-dev`
would quietly overwrite it. `pull-dev.sh` fetches them separately.

### The address requirement is declared twice

`check_if_serviceable` requires either *(street + zip)* or
*(street + city + state)*. This is expressed **declaratively on the platform
side** through `required_constraints.any_of`, rather than only described in
prose in the tool's description:

```json
"required": ["street"],
"required_constraints": {
  "any_of": [
    { "required": ["street", "zip"] },
    { "required": ["street", "city", "state"] }
  ]
}
```

The backend validates the same rule a second time with pydantic, so an
incomplete call returns `422` instead of a random result. The model guards the
contract before sending, the backend after receiving — because models are
fallible, and the quality of tool calls is the hardest part of systems like
this.

### The knowledge base is confined to a single node

The knowledge base is visible only inside the *Provide Service Information*
node, through `additional_knowledge_base`, with an empty list at agent level.

This surfaced an asymmetry in the platform worth recording: a node can narrow
**tools**, the **knowledge base** and the **prompt**, but **not procedures** —
there is no corresponding field for them. Procedures stay global to the agent
and are governed solely by their `trigger`, which is a decision made by the
model rather than a technical boundary.

---

## Simplifications

Deliberate, and a consequence of the weekend-demo format:

- **`check_if_serviceable` returns a random result.** It is a stub demonstrating
  the call contract, not a real integration.
- **One agent, two branches** (`Main` / `dev`), with no traffic splitting and no
  release process.
- **No simulation tests in CI.** The platform offers them and they are one of its
  strengths; this demo does not use them.
- **Knowledge base content is entirely fictional**, written for the demo.
- **No telephony layer** — the agent runs in a text/web channel.
- **A post-call webhook rather than post-procedure.** The platform has no hook
  for the end of a procedure; the webhook fires after the whole conversation.

---

## Development conveniences

The scripts appeared wherever the same chore came round a third time. Each is a
thin wrapper over the `elevenlabs` CLI — deliberately, so that dropping a level
down for diagnostics stays easy.

| Script | Purpose |
|---|---|
| `scripts/infra/up.sh` | backend + tunnel, prints the public address |
| `scripts/infra/list.sh` | service state, ports, links, HTTP probing |
| `scripts/infra/down.sh` | stops the infrastructure |
| `scripts/sync-dev.sh` | repo → platform, five steps, idempotent |
| `scripts/pull-dev.sh` | platform → repo, including procedures and tools |
| `scripts/kb/seed.sh` | uploads and indexes the knowledge base |
| `scripts/list-agents.sh` | agents, branches, traffic share, drafts |
| `scripts/test-solution.sh` | ruff, pyright, JSON/TOML, compose, `bash -n` |

### Things that cost time, and are documented

- **`agents pull` without `--update` quietly does nothing** — it skips an
  existing agent and exits 0.
- **`--branch <id>` corrupts `agents.json`** — it registers the branch under its
  ID rather than its name and creates a duplicate entry.
- **`compute_rag_index` is asynchronous** — it returns `created` while the index
  builds in the background; without polling, the script would report success on
  an unfinished index.
- **`workflow.subgraphs` appears in the response but is rejected in a request.**
- **A long payload passed as an argument fails on Windows** — the body goes
  through stdin (`--json -`).
- **`agents push` is not a full synchronisation.** It skips a knowledge base
  attached to a workflow node, drops test attachments, and can null a field
  governed by a pairing rule — `reasoning_effort` only survives when sent
  together with `llm`. This is why `sync-dev.sh` runs five steps rather than one
  push.
- **After a tunnel restart, `sync-dev.sh` has to run again**, because the tool
  and the webhook then point at a dead address — the tool definition holds a URL
  placeholder that each run substitutes.

---

## Layout

```
agent_configs/        agent configuration, procedures, tools, knowledge base
backend/              FastAPI — webhooks called by the agent
scripts/              CLI tooling (.sh wrappers plus helpers in .internal/)
docs/dev-loop.md      full documentation of the working loop
```

---

## License

MIT — see [`LICENSE`](LICENSE).
