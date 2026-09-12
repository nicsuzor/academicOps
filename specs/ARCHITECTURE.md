# academicOps Architecture

The authoritative description of what this repository is and how it is built.
Everything here is current state. Nothing here is history.

## Repository layout

```
lib/                    Shared source, never shipped as-is. Most of it is injected
                        into plugin build trees; the rest feeds the image build.
  agy/                  Shared config for the agy client.
  hooks/                Hook runtime shared by every plugin that hooks
                        (dispatch.py).
  polecat/              The container launcher, its entrypoint and baked image
                        defaults; injected into `plugins/aops`.
  py/                   Shared Python helpers, including the transcript
                        pipeline (`py/transcripts/`).
  telemetry/            Shared observability config, injected into whichever
                        plugin ships a given skill's references.
build/                  Build system: stages, client adapters, marketplace
                        generation.
templates/              Build-time file templates, GitHub Actions workflow
                        templates, and the GitHub-agent worker template.
scripts/                Repo tooling, not shipped in any plugin.
plugins/                Plugin sources. Only what a client needs.
  aops/                 james (container worker), marsha (QA), sara
                        (supervisor); review and workflow-composition skills;
                        observability hooks; the polecat CLI.
  ida/                  ida -- the interactive face, and the only agent that
                        talks to the user.
  pkb/                  pauli -- sole writer to the Personal Knowledge Base;
                        memory, capture, and workflow-template skills; the
                        PKB MCP server.
  rbg/                  rbg -- rule enforcement: an advisory turn-by-turn
                        evaluator plus a stop-side rule-check gate.
  tools/                Domain research skills.
  ts/                   Tailscale bring-up for remote/cloud sessions.
  aops-debug/           Debug plugin that dumps raw hook payloads.
plugins.disabled/       Retired sources, excluded from the build.
specs/                  Design intent.
tests/                  Test suite.
.agents/                Rules for agents working ON this repository.
```

A plugin source directory contains only files the client loads, plus its
README: `agents/`, `skills/`, `hooks/`, `manifest/`, `scripts/`, `README.md`.
Tests, specs, and development tooling live outside `plugins/`.

## Plugins

`build/marketplace.toml` maps directory to marketplace name and is the single
source of truth for the built plugin set.

| Directory            | Owns                                                                                                                                                                                                                                                 |
| -------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `plugins/aops`       | james (`plugins/aops/agents/james.md`), marsha (`plugins/aops/agents/marsha.md`), sara (`plugins/aops/agents/sara.md`); review, workflow-composition, hydrate, and learn skills; the polecat CLI (`lib/polecat` injected here); observability hooks. |
| `plugins/ida`        | ida (`plugins/ida/agents/ida.md`) -- the interactive face and the only agent that talks to the user.                                                                                                                                                 |
| `plugins/pkb`        | pauli (`plugins/pkb/agents/pauli.md`) -- sole writer to the PKB; capture, memory, decomposition, and workflow-template skills; the `services` PKB MCP server.                                                                                        |
| `plugins/rbg`        | rbg (`plugins/rbg/agents/rbg.md`) -- rule enforcement: an advisory turn-by-turn evaluator plus a stop-side rule-check gate.                                                                                                                          |
| `plugins/tools`      | Domain research skills (data analysis, document conversion, diagramming, peer review, project scaffolding).                                                                                                                                          |
| `plugins/ts`         | Tailscale bring-up for remote/cloud sessions.                                                                                                                                                                                                        |
| `plugins/aops-debug` | Debug plugin that dumps raw hook payloads.                                                                                                                                                                                                           |

Each plugin's own `README.md` is the fuller description; this table is not a
second copy of it.

## Hooks

Every plugin hook shares one runtime, `lib/hooks/dispatch.py`, injected at
build time. Which client-visible events fire, in what order, and the
`refuse` / `block` / advisory disposition contract are stated there; this
table names only which plugin registers which event and to what end, read
from each plugin's own hooks/handlers.py (e.g. `plugins/aops/hooks/handlers.py`):

| Plugin | Events registered                                                                                                               | What it's for                                                                                                                                                                                              |
| ------ | ------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `aops` | `SessionStart`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `PostToolUseFailure`, `Stop`, `PostToolBatch`, `SubagentStart` | Session credential/path setup, OTel tracing spans, the honesty reminder on subagent spawn, and the quiet/hearsay advisories on `PostToolBatch`.                                                            |
| `ida`  | `PreToolUse`, `Stop`                                                                                                            | `PreToolUse` runs the premise-check handler; `Stop` is registered with no handlers yet.                                                                                                                    |
| `pkb`  | `UserPromptSubmit`                                                                                                              | Grounds the incoming prompt in a PKB search before the agent replies.                                                                                                                                      |
| `rbg`  | `PreToolUse`, `Stop`, `SubagentStop` (declared, unwired)                                                                        | Rule-compliance evaluation and the stop-side rule-check gate, as designed. `HANDLERS` in `plugins/rbg/hooks/handlers.py` currently has every entry commented out, so this pillar ships no live hook today. |
| `ts`   | `SessionStart`                                                                                                                  | Joins the tailnet when `CLAUDE_CODE_REMOTE=true` and `TS_AUTHKEY` is set.                                                                                                                                  |

`plugins/tools` and `plugins/aops-debug` ship no hooks or a debug-only
passthrough respectively; see each plugin's own README.

## Build

`build/build.py` assembles `dist/<plugin>-<client>` for each plugin and
client. Stages, in order: **inject** (copy each plugin's declared `lib/`
content into its build tree, per `manifest/plugin.toml`'s `[[shared]]`
entries), **render manifests** (merge each `manifest/*.template.json`'s
`clients.__base__` with its `clients.<client>` section), **adapt to client**
(client-specific transforms in `build/clients/`), and **package** (tar per
client). Then `build/marketplace.py` generates the marketplace manifests,
including the `dist/cowork/` and `dist/openclaw/` directory-marketplace
channels.

### Client adapters

A client adapter is the only place a client-specific workaround may live.

`build/clients/claude.py`:

- `manifest/plugin.json` -> `.claude-plugin/plugin.json`
- `manifest/hooks.json` -> `hooks/hooks.json` (the only path Claude Code reads)
- `manifest/mcp.json` -> `.mcp.json`

`build/clients/openclaw.py`:

- `manifest/plugin.json` -> `.claude-plugin/plugin.json`
- `manifest/hooks.json` -> `hooks/hooks.json`
- `manifest/mcp.json` -> `.mcp.json`
- axioms carrying `trigger: always_on` -> `axioms.jsonl`

`build/clients/agy.py`:

- `manifest/plugin.json` -> `plugin.json`
- `manifest/hooks.json` -> `hooks.json`, reshaped from the Claude Code hook
  schema
- `manifest/mcp.json` -> `mcp_config.json`

An agent's `tools:` list is translated into agy's accepted vocabulary through
`build/tool_map.toml`. Full detail on the vocabulary contract, translation
edge cases, and what each client omits belongs to `build/clients/agy.py`
itself, not restated here.

## Containers

Polecat (`lib/polecat/`, injected into `plugins/aops`) launches isolated
Docker containers that boot into the `james` persona and run one unit of
work to completion, writing results back to the PKB task record. See
[polecat-system.md](polecat/polecat-system.md) for the full contract.
