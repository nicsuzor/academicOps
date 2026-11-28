# academicOps Architecture

The authoritative description of what this repository is and how it is built.
Everything here is current state. Nothing here is history.

## Repository layout

```
lib/                    Shared source, never shipped as-is. Most of it is injected
                        into plugin build trees; the rest feeds the image build.
  agy/                  Shared config for the agy client.
  hooks/                Hook runtime shared by every plugin that hooks
                        (dispatch.py), and the OTel span pipeline
                        (claude_code_tracer.py) that crew's tracing hooks,
                        ida's verdict spans and aops-debug's debug spans use.
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
                        talks to the user; argdown-toulmin and premise-check
                        skills; session and premise-check hooks.
  crew/                 The crew: james, marsha and pauli (the custodian for
                        PKB graph, planning, and all knowledge tasks); the
                        axioms skill and the working skills (pull, reify, dump,
                        workflow-library, review, capture, memory,
                        planning); session setup, PKB
                        prompt grounding, and the OTel tracing hooks.
  sara/                 Polecat dispatch only: the sara agent and the
                        dispatch skill.
  tools/                Domain research skills.
  aops-debug/           Debug plugin that dumps raw hook payloads.
  ida-telegram/         Ida's custom Telegram channel and Mini App plugin.
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

| Directory | Owns |
| - | - |
| `plugins/ida` | ida (`plugins/ida/agents/ida.md`) -- the interactive face and the only agent that talks to the user; the `argdown-toulmin` and `premise-check` skills; session and premise-check hooks. |
| `plugins/sara` | Polecat dispatch and nothing else: sara (`plugins/sara/agents/sara.md`) and the `dispatch` skill (`plugins/sara/skills/dispatch/`), which launches isolated polecat containers on reified tasks. One `SessionStart` hook that injects its `CORE.md`. |
| `plugins/crew` | The crew: james (`plugins/crew/agents/james.md`), marsha (`plugins/crew/agents/marsha.md`), and pauli (`plugins/crew/agents/pauli.md`) -- the knowledge base custodian for memory, planning, decomposition, graph writes, and every knowledge task (questions, finding things, web, GitHub, read-only code inspections, and config lookups); the `axioms` skill whose files are the axioms (`plugins/crew/skills/axioms/`); the working skills (`plugins/crew/skills/`: pull, reify, dump, q, decompose, strategize, remember, learn, craft, verify, strategic-review, and workflow-library); session setup, PKB prompt grounding, and the OTel tracing hooks -- the only plugin that registers them. |
| `plugins/tools` | Domain research skills (data analysis, document conversion, diagramming, peer review, project scaffolding). |
| `plugins/aops-debug` | Debug plugin that dumps raw hook payloads. |
| `plugins/ida-telegram` | Ida's custom Telegram channel and Mini App plugin: stdio MCP channel server, progressive disclosure with expandable blockquotes, async question broker, feedback trace collection, Mini App (Details, Review, Questions, Anchor), voice notes, and role-gated polling. |

Each plugin's own `README.md` is the fuller description; this table is not a
second copy of it.

## Hooks

Every plugin hook shares one runtime, `lib/hooks/dispatch.py`, injected at
build time. Which client-visible events fire, in what order, and the
`refuse` / `block` / advisory disposition contract are stated there; this
table names only which plugin registers which event and to what end, read
from each plugin's own hooks/handlers.py (e.g. `plugins/ida/hooks/handlers.py`).

One surface is excepted. In a Claude Cowork session (the Claude desktop app's
Cowork surface) the ida hooks do nothing: no handler runs and no fire is
logged, because Cowork sessions carry none of the environment `SessionStart`
needs. The decision is `is_cowork` in `lib/hooks/dispatch.py`, made once in
`dispatch.py` before any other work, from Claude Code's own signal in the
hook's inherited environment: `CLAUDE_CODE_IS_COWORK` set to `1` or `true`, or
`CLAUDE_CODE_ENTRYPOINT` set to a Cowork entrypoint (`local-agent`,
`local_agent`, `remote_cowork`, `remote_cowork_trigger`). Every other surface
-- the CLI, the desktop app's Code tab, cloud sessions, agy -- runs normally.
Plugin hooks never rewrite or inject MCP tool-call inputs, and agents never pass caller-correlation `session_id` tool arguments; programmatic HTTP callers propagate W3C `traceparent` and `baggage` in `params._meta` and HTTP headers while client hook tracers own session grouping for Code Mode calls.

| Plugin | Events registered | What it's for |
| - | - | - |
| `ida` | Claude Code: `SessionStart`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `PostToolBatch`, `SubagentStart`, `Stop`, `SubagentStop`. agy: `SessionStart`, `PreInvocation` (canonical `UserPromptSubmit`), `PreToolUse`, `PostToolUse`, `Stop` | `SessionStart` injects ida's `CORE.md` and the premise-check pointer; `SubagentStart` uniform `honesty.md` reminders with recipient `--agent` and armed-claim context; incoming report reminders (`hearsay.md`); recipient-scoped `(session_id, agent_id)` `hearsay_gate` (`premise_check_gate`) arming across `UserPromptSubmit`, `PostToolUse`, `PostToolBatch`, and `SubagentStop`, enforced per agent on `PreToolUse` and `Stop` (see [evidence contract enforcement](enforcement/evidence-contract-enforcement.md)). Registers no lifecycle tracing; the premise-check verdict script ships one verdict span per verdict through the shared span pipeline. |
| `crew` | Claude Code: `SessionStart`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `PostToolUseFailure`, `Stop`, `SubagentStop`, `StopFailure`, `PermissionRequest`, `PermissionDenied`, `Notification`, `PreCompact`, `PostCompact`, `SessionEnd`. agy: `SessionStart`, `PreInvocation` (canonical `UserPromptSubmit`), `PreToolUse`, `PostToolUse`, `Stop` | Session setup (`SessionStart` metadata, crew `CORE.md`, credential isolation into `CLAUDE_ENV_FILE`); `UserPromptSubmit` PKB prompt grounding ([prompt hydration](agents/prompt-hydration.md)); and OTel tracing on every registered event except `SessionStart` -- `claude_code_tracer` on Claude Code, `agy_tracer` on agy -- the only plugin that registers lifecycle tracing. Rule-compliance evaluation and the stop-side rule-check gate are not wired: their sources sit in `plugins/crew/cope_hooks_disabled/`. |

`plugins/tools` and `plugins/sara` each register only a `SessionStart` hook that injects their `CORE.md`.
`plugins/aops-debug` is an opt-in
debug passthrough: on every event it appends the raw payload to a temp-file
JSONL and, when a trace endpoint is set, exports one debug span carrying that
payload into the session's trace. It is not lifecycle tracing, which crew alone
registers.

## Build

`build/build.py` assembles `dist/<plugin>-<client>` for each plugin and
client. Stages, in order: **inject** (copy each plugin's declared `lib/`
content into its build tree, per `manifest/plugin.toml`'s `[[shared]]`
entries), **render manifests** (merge each `manifest/*.template.json`'s
`clients.__base__` with its `clients.<client>` section), **adapt to client**
(client-specific transforms in `build/clients/`), and **package** (tar per
client). Then `build/marketplace.py` generates the marketplace manifests,
including the `dist/cowork/` and `dist/openclaw/` directory-marketplace
channels and `dist/plugins/` (Antigravity's native multi-plugin directory,
populated from `dist/<plugin>-agy`).

### Client adapters

A client adapter is the only place a client-specific workaround may live.

`build/clients/claude.py`:

- `manifest/plugin.json` -> `.claude-plugin/plugin.json`
- `manifest/hooks.json` -> `hooks/hooks.json` (the only path Claude Code reads)
- `manifest/mcp.json` -> `.mcp.json`
- `manifest/auto-mode.json` -> `auto-mode.json` (curated `autoMode` classifier rules)

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
