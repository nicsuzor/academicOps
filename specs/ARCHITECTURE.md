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
  ida/                  ida -- the interactive face, and the only agent that
                        talks to the user; james, marsha, sara, pauli (the
                        PKB graph agent) and rbg; PKB, workflow, review and
                        premise-check skills; session, PKB-search, tracing
                        and premise-check hooks.
  rbg/                  Rule enforcement: the axioms, an advisory
                        turn-by-turn evaluator plus a stop-side rule-check
                        gate.
  tools/                Domain research skills.
  aops-debug/           Debug plugin that dumps raw hook payloads.
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

| Directory            | Owns                                                                                                                                                                                                                                                                                                                                                                                                        |
| -------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `plugins/ida`        | ida (`plugins/ida/agents/ida.md`) -- the interactive face and the only agent that talks to the user; james, marsha, sara, rbg, and pauli (`plugins/ida/agents/pauli.md`) -- the PKB graph agent for memory, planning, decomposition, and graph writes; capture, memory, decomposition, dispatch, workflow-library, review, and premise-check skills; session, PKB-search, tracing, and premise-check hooks. |
| `plugins/rbg`        | Rule enforcement: the axioms (`plugins/rbg/axioms/`), an advisory turn-by-turn evaluator plus a stop-side rule-check gate. The rbg agent itself is `plugins/ida/agents/rbg.md`.                                                                                                                                                                                                                             |
| `plugins/tools`      | Domain research skills (data analysis, document conversion, diagramming, peer review, project scaffolding).                                                                                                                                                                                                                                                                                                 |
| `plugins/aops-debug` | Debug plugin that dumps raw hook payloads.                                                                                                                                                                                                                                                                                                                                                                  |

Each plugin's own `README.md` is the fuller description; this table is not a
second copy of it.

## Hooks

Every plugin hook shares one runtime, `lib/hooks/dispatch.py`, injected at
build time. Which client-visible events fire, in what order, and the
`refuse` / `block` / advisory disposition contract are stated there; this
table names only which plugin registers which event and to what end, read
from each plugin's own hooks/handlers.py (e.g. `plugins/ida/hooks/handlers.py`):

| Plugin | Events registered                                                                                                                                                                                                                                                                                                                                        | What it's for                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `ida`  | Claude Code: `SessionStart`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `PostToolUseFailure`, `PostToolBatch`, `Stop`, `SubagentStop`, `StopFailure`, `PermissionRequest`, `PermissionDenied`, `Notification`, `PreCompact`, `PostCompact`, `SessionEnd`. agy: `PreInvocation` (canonical `UserPromptSubmit`), `PreToolUse`, `PostToolUse`, `Stop` | Session credential/path setup and session-id export on `SessionStart`; OTel tracing spans; on `UserPromptSubmit`, grounds the user's prompt in a PKB search (`search_the_pkb`, see [prompt hydration](agents/prompt-hydration.md)) and flags a peer report as hearsay for ida and sara; the premise-check gate, armed on `UserPromptSubmit`, `PostToolUse` and `PostToolBatch` and enforced on `PreToolUse` and `Stop` (see [report verification](enforcement/report-verification.md)). |
| `rbg`  | `PreToolUse`, `Stop`, `SubagentStop` (declared, unwired)                                                                                                                                                                                                                                                                                                 | Rule-compliance evaluation and the stop-side rule-check gate, as designed. `HANDLERS` in `plugins/rbg/hooks/handlers.py` currently has every entry commented out, so this pillar ships no live hook today.                                                                                                                                                                                                                                                                              |

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

The polecat worker container image and its launcher (`polecat`) are maintained outside this repository and supplied by the installer, together with any Docker MCP server registered behind the `services` portal.
