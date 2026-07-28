# academicOps Architecture

The authoritative description of what this repository is and how it is built.
Everything here is current state. Nothing here is history.

## Repository layout

```
lib/                    Shared source. Never shipped as-is; injected at build time.
  axioms/               The axioms. Single source of truth.
  doctrine/             Composable agent-instruction fragments.
  hooks/                Hook runtime shared by every plugin that hooks.
  py/                   Shared Python helpers.
  manifest/             Shared manifest fragments.
build/                  Build system.
plugins/                Plugin sources. Only what a client needs.
  aops/                 james, marsha, rbg, review + dispatch skills, polecat.
  pkb/                  pauli, memory, planning, workflow composition, MCP client config.
  ida/                  ida — the interactive face.
  cope/                 Automatic rule enforcement hooks.
  ts/                   Tailscale bring-up.
  tools/                Domain research skills.
specs/                  Design intent.
tests/                  Test suite.
.agents/                Rules for agents working ON this repository.
```

A plugin source directory contains only files the client loads, plus its README:
`agents/`, `commands/`, `skills/`, `hooks/`, `axioms/`, `scripts/`, `manifest/`,
`README.md`. Tests, specs, and development tooling live outside `plugins/`. The
README's audience, its contents, and its split with `specs/` are governed by the
docs entry in [meta/doc-taxonomy.md](meta/doc-taxonomy.md).

## Binding constraints

**No duplication.** Any file needed by two or more plugins lives in `lib/` and is
copied in at build time. A second copy of anything in `lib/` is a build failure.

**No defaults.** No endpoint, URL, host, path, token, or credential is baked into
any shipped artifact. Every such value arrives from the environment or from
client `userConfig`. Our code and a client's installation are strictly separate.

**Instructions are operative.** Agent, skill, and command files say what to do
now. No history, no rationale, no changelogs, no deprecation notices, no
backwards-compatibility notes, no decision logs. Explanation belongs in `specs/`.

**Loose coupling.** A plugin may depend on `lib/`. A plugin never reads another
plugin's files.

## Plugins

Directory names are short; marketplace names carry the `aops` prefix.

| Directory       | Marketplace name | Owns                                                                            |
| --------------- | ---------------- | ------------------------------------------------------------------------------- |
| `plugins/aops`  | `aops`           | james, marsha, rbg. Review, QA, verification, dispatch, polecat containers.     |
| `plugins/pkb`   | `aops-pkb`       | pauli. Memory, effectual planning, workflow composition, PKB MCP client config. |
| `plugins/ida`   | `aops-ida`       | ida. The interactive face.                                                      |
| `plugins/cope`  | `aops-cope`      | Automatic in-session rule enforcement.                                          |
| `plugins/ts`    | `aops-ts`        | Tailscale bring-up for remote sessions.                                         |
| `plugins/tools` | `aops-tools`     | Domain research skills.                                                         |

### aops

**james** synthesises and dispatches. He commissions review agents, interrogates
their output, resolves conflicting verdicts into one judgment, and delegates
substantive work — either to a supervised in-session agent team or to an
asynchronous polecat container. Ida delegates to james; james never talks to the
user.

**marsha** judges whether an artifact is outstanding. She runs it.

**rbg** judges rule compliance. She applies three rule sources in order:

1. `axioms/` shipped in the plugin — the floor, inviolable
2. `$CWD/.agents/rules/` — project-local rules
3. `$ACA_DATA/.agents/rules/` — user-scoped rules from the PKB repo

Later sources add obligations. They never weaken an axiom.

### pkb

**pauli** is the sole writer to the PKB. No other agent mutates it.

The PKB holds current state, synthesised. Not an append log. Writing to it means
reading what is there, integrating the new fact, and leaving one correct
document. Timestamped history entries, decision logs, deprecation notices, and
changelogs are prohibited content.

Workflow composition: the plugin ships a process-template library under
`workflows/`. Templates in `$ACA_DATA/.agents/workflows/` override and extend it
by filename. Pauli composes a workflow for the work in front of it by reading
templates, never by parsing or solving them.

MCP: the plugin ships client wiring only — transport config, the stdio launcher,
and a `userConfig` field for the server URL. The server itself is external.

### ida

The interactive face, and the only agent that talks to the user. Academic
integrity is non-negotiable. Ida holds between steps, answers what it can
answer, delegates everything substantive to james, and filters what comes back so
the user sees only what needs their judgment.

### cope

Enforces the same three rule sources as rbg, automatically, in-session, via
hooks. Where rbg is asked, cope is always on.

## Hooks

The complete set. Each hook's injected wording lives in a markdown file next to
it, under `hooks/messages/`, and is editable without touching code.

Events are named canonically. `agy` fires five events of its own, two of which
carry a canonical event: `PreInvocation` is `UserPromptSubmit`, `PostInvocation`
is `Stop`. It has no session-level event, so `SessionStart` and `SessionEnd`
cannot fire there at all.

| Plugin | Event              | Client   | Effect                                                                                                                                                                           |
| ------ | ------------------ | -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `pkb`  | `UserPromptSubmit` | both     | Inject relevant PKB context, or instruct the agent to search for it.                                                                                                             |
| `aops` | `SessionStart`     | `claude` | Credential isolation for container sessions. Report telemetry configuration.                                                                                                     |
| `aops` | `SubagentStop`     | `claude` | Remind the stopping subagent to present its answer with checkable evidence. The output reaches the agent that is stopping, not its parent.                                       |
| `aops` | `Stop`             | both     | Remind the agent that is stopping to present its answer with checkable evidence. Same handler and message as `SubagentStop` — the events differ only in which agent is stopping. |
| `aops` | `PreToolUse`       | `claude` | Refuse an interactive prompt in a headless session.                                                                                                                              |
| `cope` | `PreToolUse`       | `claude` | Rule enforcement.                                                                                                                                                                |
| `cope` | `UserPromptSubmit` | `agy`    | State the live rule set for the turn, on the surface where the evaluator has no tool call to judge.                                                                              |
| `ts`   | `SessionStart`     | `claude` | Tailscale bring-up.                                                                                                                                                              |
| `ts`   | `SessionEnd`       | `claude` | Ship session transcripts to the configured host.                                                                                                                                 |

Seven of the nine fire on one client only. `ts` ships no agy `hooks.json` at all,
so neither Tailscale bring-up nor transcript sync happens there.

One hook refuses rather than advises: a headless session cannot answer an
interactive prompt, so asking one hangs the session until it times out. That is
a capability fact, not a rule verdict, and it is the only blocking hook.

Anything else a session needs is a workflow, not a hook.

All hooks share one runtime in `lib/hooks/`, injected into each plugin at build
time. A hook that cannot load its message file fails loudly.

The runtime reports its own degradation on the response, not only on stderr,
which nothing renders to the person in the session: a handler that raised, a
rule file that could not be read, an evaluator that did not answer. Once per
session per kind of fault, never as a permission decision, and never for the
absence of a mechanism nobody configured.

## Observability

Claude Code's native OpenTelemetry export is the tracing mechanism. It is
session-scoped, so enabling it once covers every plugin; no plugin emits its own
spans.

The framework defines the env contract and forwards it — into polecat containers,
into Docker, into scheduled runs. It sets no values. `aops`'s `SessionStart` hook
reports whether telemetry is configured and stays silent about what it should be.

Contract (`lib/hooks/telemetry.py` `CONTRACT`): `CLAUDE_CODE_ENABLE_TELEMETRY`,
`CLAUDE_CODE_ENHANCED_TELEMETRY_BETA`, `OTEL_METRICS_EXPORTER`,
`OTEL_LOGS_EXPORTER`, `OTEL_TRACES_EXPORTER`, `OTEL_EXPORTER_OTLP_ENDPOINT`,
`OTEL_EXPORTER_OTLP_PROTOCOL`, `OTEL_RESOURCE_ATTRIBUTES`,
`OTEL_LOG_USER_PROMPTS`, `OTEL_LOG_RAW_API_BODIES`, `OTEL_LOG_TOOL_DETAILS`,
`OTEL_LOG_ASSISTANT_RESPONSES`, `OTEL_METRIC_EXPORT_INTERVAL`,
`OTEL_LOGS_EXPORT_INTERVAL`, `OTEL_TRACES_EXPORT_INTERVAL`.

A `SessionStart` hook subprocess cannot observe all 15: confirmed empirically,
setting every `OTEL_*` var at session-launch time still leaves a live hook
reading none of them, while the same session's tool calls see them fine (a
separate, settings-managed environment, not the hook's). Only the two
`CLAUDE_CODE_*` feature flags reliably reach a hook subprocess. The
`SessionStart` report therefore counts against those two
(`telemetry.ENABLEMENT_VARS`), not the full 15 — counting the unreachable
`OTEL_*` half would report a gap that correct configuration could never
close. The full 15-var contract still governs what
`plugins/aops/polecat/env_contract.py` forwards into containers and CI, where
no such hook-subprocess restriction applies.

## Build

`build/build.py` assembles `dist/<plugin>-<client>` for each plugin and client.

Stages, in order:

1. **Inject.** Copy `lib/` content a plugin declares into the plugin's build
   tree. Declared in the plugin's `manifest/plugin.toml` under `[shared]`.
2. **Resolve includes.** Replace each `@include <path>` line in a markdown file
   with the content of that file from `lib/`. Recursive.
3. **Render manifests.** Merge `manifest/*.template.json` `__base__` with the
   client's section, and write to the client's expected path.
4. **Adapt to client.** Client adapters in `build/clients/` apply the
   client-specific transformations.
5. **Package.** Tar per client, plus the marketplace manifests.
6. **Cowork channel.** `dist/cowork/` — a directory marketplace assembled from
   the built claude dists: one directory per plugin, a
   `<plugin>-v<version>.zip` upload archive per plugin, and
   `.claude-plugin/marketplace.json` naming the marketplace
   `academicOps-cowork`. Claude-only; skipped when `claude` is not in the
   client list.

### Client adapters

`build/clients/claude.py`

- `manifest/plugin.json` → `.claude-plugin/plugin.json`
- `manifest/hooks.json` → `hooks/hooks.json` (the only path Claude Code reads)
- `manifest/mcp.json` → `.mcp.json`
- `axioms/*.md` with `trigger: always_on` → `axioms.jsonl`, merged into
  `~/.claude/settings.json` at install time

`build/clients/agy.py`

- `manifest/plugin.json` → `plugin.json`
- `manifest/hooks.json` → `hooks.json`, script paths unquoted (agy execs via argv)
- `manifest/mcp.json` → `mcp_config.json`
- `commands/<name>.md` → `skills/cmd-<name>/SKILL.md`
- `axioms/*.md` with `trigger: always_on` → `rules/*.md`

A client adapter is the only place a client-specific workaround may live. Adding a
plugin requires no change to any adapter.

## Installation

Installation is the only stage permitted to touch a client installation, and it
touches only what it declares.

Claude Code applies always-on rules through `autoMode` in
`~/.claude/settings.json`, which it reads only from that file. The build emits
`axioms.jsonl`; the installer merges it in. That merge:

- writes only under a key it owns, and never replaces a whole settings block it
  did not author
- is idempotent, and removable by the uninstall target
- fails loudly and non-zero when it cannot do what it claims

## Enforcement

Two in-session mechanisms, both advisory, both live:

- `autoMode` — Claude Code's own classifier, fed the axioms via `axioms.jsonl`
- `cope` — hook-based rule evaluation

They overlap deliberately. Which one works better is an open question, so both
ship and neither is built as though it were the gate.

Real enforcement is a separate merge-stage check. Nothing in-session blocks on a
rule verdict.

## Containers

Every plugin works in a fully isolated container: no host paths, no host
credentials, no network assumptions beyond what the environment supplies. The
container receives configuration through the environment only.

Polecat runs asynchronous work in these containers. James dispatches to it.
