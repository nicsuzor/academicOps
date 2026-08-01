# academicOps Architecture

The authoritative description of what this repository is and how it is built.
Everything here is current state. Nothing here is history.

## Repository layout

```
lib/                    Shared source, never shipped as-is. Most of it is injected
                        into plugin build trees; the rest feeds the image build.
  axioms/               The axioms. Single source of truth.
  hooks/                Hook runtime shared by every plugin that hooks.
  py/                   Shared Python helpers.
  manifest/             Shared manifest fragments.
  polecat/              The container launcher, its entrypoint and baked image
                        defaults. Runtime modules inject into the plugin that
                        dispatches containers; `defaults/` and `entrypoint.sh`
                        are build-context inputs to the image, not plugin files.
build/                  Build system.
plugins/                Plugin sources. Only what a client needs.
  pkb/                  pauli, memory, planning, workflow composition, MCP client config.
  ida/                  ida — the interactive face.
  orchestrate/          james — synthesis and dispatch; marsha — QA.
  rbg/                  rbg — rule enforcement: an advisory turn-by-turn evaluator plus a
                        stop-side rule-check gate.
  ts/                   Tailscale bring-up.
  tools/                Domain research skills.
  aops-debug/           Debug plugin that dumps raw hook payloads.
plugins.disabled/       Retired plugin sources, excluded from the build.
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

## Core Pillars

academicOps is structured around **4 core pillars**:

1. **Prompt Situation (`pkb`):** Ground incoming prompts in strategic PKB history via `UserPromptSubmit` hook + `hydrate`/`situate`.
2. **Workflow Composition (`pkb`):** Select task-appropriate assurance and review levels (`workflow`) matching risk and blast radius.
3. **Containerized Execution & Dispatch (`orchestrate`):** Dispatch tasks to isolated Docker containers (`lib/polecat`, injected into `orchestrate`), writing results back to the PKB task record, committing changes, and pushing.
4. **Dual-Layer Rule Enforcement (`rbg`):** Turn-by-turn local model evaluation of tool calls (`PreToolUse`), plus a stop gate that blocks once per stop-chain and directs the agent to run the RBG rule compliance check (`axioms/` + project + local rules) before stopping (`Stop` / `SubagentStop`).

## Plugins

Directory names are short. `build/marketplace.toml` maps directory →
marketplace name and is the single source of truth for the built plugin set.

| Directory             | Marketplace name | Owns                                                                                |
| --------------------- | ---------------- | ----------------------------------------------------------------------------------- |
| `plugins/pkb`         | `pkb`            | pauli. Memory, effectual planning, workflow composition, PKB MCP client config.     |
| `plugins/ida`         | `ida`            | ida, the interactive face.                                                          |
| `plugins/orchestrate` | `orchestrate`    | james, synthesis and dispatch; marsha, QA.                                          |
| `plugins/rbg`         | `rbg`            | rbg. Rule enforcement: turn-by-turn evaluator advisory and the stop-side rule gate. |
| `plugins/ts`          | `ts`             | Tailscale bring-up for remote sessions.                                             |
| `plugins/tools`       | `tools`          | Domain research skills.                                                             |
| `plugins/aops-debug`  | `aops-debug`     | Debug plugin that dumps raw hook payloads.                                          |

### pkb

**pauli** is the sole writer to the PKB. No other agent mutates it.

The PKB holds current state, synthesised. Not an append log. Writing to it means
reading what is there, integrating the new fact, and leaving one correct
document.

Workflow composition: the plugin ships a process-template library under
`workflows/`. Pauli composes a workflow for the work in front of it by reading
templates, matching the required QA assurance level to the task.

The plugin hooks `UserPromptSubmit` and nothing else. A stop gate is intended
here — while the session still holds an `in_progress` task, block once per
stop-chain and direct the agent to record its work and release it, fail-CLOSED —
but it is not built, and cannot be until the task store can answer which tasks a
given session holds.

### ida

The interactive face, and the only agent that talks to the user. Academic
integrity is non-negotiable. Ida holds between steps, answers what it can
answer, delegates everything substantive to james, and filters what comes back so
the user sees only what needs their judgment.

### orchestrate

Ships **james**, who synthesises and dispatches. He commissions review agents,
interrogates their output, resolves conflicting verdicts into one judgment,
and delegates substantive work — either to a supervised in-session agent team
or to an asynchronous polecat container. Ida delegates to james; james never
talks to the user.

**marsha** judges whether an artifact is outstanding. She runs it. Her `verify`
skill is bound to her and ships alongside her.

She ships here rather than in a plugin of her own, and that is a deliberate
call rather than a consequence of how she is reached. Co-location buys nothing
at dispatch: james reaches `rbg:rbg` and `pkb:pauli` across plugin boundaries
by namespace, and would reach marsha the same way from anywhere. What decides
it is that `rbg` and `pkb` exist around infrastructure only their owner needs —
rbg's `PreToolUse` and `Stop` hooks, pkb's MCP client config — while marsha
carries none: an agent body and one bound skill, no hooks, no config, no
`lib/` injection. A plugin of her own would be a namespace and nothing else, so
she ships with the review machinery that commissions her.

Her independence is unaffected, because it never rested on packaging. It comes
from reviewing blind to the other reviewers and from james treating every
verdict as input rather than truth (`plugins/orchestrate/skills/strategic-review/SKILL.md`).
What packaging does decide is whether she resolves at all: a shipping
instruction naming a reviewer who does not ship leaves the review short-handed
while reading as complete.

### rbg

**rbg** judges rule compliance. She applies three rule sources in order:

1. `axioms/` shipped in the plugin — the floor, inviolable
2. `$CWD/.agents/rules/` — project-local rules
3. `$ACA_DATA/.agents/rules/` — user-scoped rules from the PKB repo

Later sources add obligations. They never weaken an axiom.

The plugin advises on the same three sources automatically, in-session, on one
surface: a parallel turn-by-turn `PreToolUse` hook running a lightweight local
Reflexes LLM evaluator model. It returns `warn`, so a flagged call still
proceeds.

There is also a stop-side rule gate, and it ships. `plugins/rbg/hooks/handlers.py`
registers `Stop` and `SubagentStop`, alongside `PreToolUse` and
`UserPromptSubmit`. On both stop events it withholds the stop once per
stop-chain (`block`, `lib/hooks/dispatch.py`), directing the agent to run the
RBG rule-compliance check over the three sources above and present checkable
evidence before it stops. See Hooks and Enforcement below for the full
behaviour.

## Hooks

Master Hook Lifecycle Matrix. Every hook is deterministic, lightweight, and single-purpose:

| Plugin        | Event                                   | Target Client            | Required Context / Env                         | Injected Payload / Action                                                                                                                                                                                                                                                                                                                                          | WHY (Purpose & Rationale)                                                                                                                                                                                                                                                                                                                              |
| :------------ | :-------------------------------------- | :----------------------- | :--------------------------------------------- | :----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `pkb`         | `UserPromptSubmit`                      | Both (Claude Code & AGY) | `PKB_MCP_URL`                                  | Strategic context search instructions & relevant PKB history.                                                                                                                                                                                                                                                                                                      | **Pillar 1 (Situation):** Ground every user prompt in historical knowledge and prior decisions before acting.                                                                                                                                                                                                                                          |
| `rbg`         | `PreToolUse`                            | Claude Code              | `COPE_EVALUATOR_*` (Local LLM model)           | Parallel rule compliance advisory with matched rule text & reasoning.                                                                                                                                                                                                                                                                                              | **Pillar 4 (Enforcement L1):** Non-blocking, turn-by-turn evaluation of tool calls against active rules via a fast local model.                                                                                                                                                                                                                        |
| `rbg`         | `UserPromptSubmit`                      | AGY (`PreInvocation`)    | Live rule set files                            | Summary roster of active rules for the turn.                                                                                                                                                                                                                                                                                                                       | Provides rule visibility on surfaces that lack tool-call interception.                                                                                                                                                                                                                                                                                 |
| `orchestrate` | `PostToolUse` (`Agent`)                 | Claude Code              | none                                           | Non-blocking reminder (`warn`) that a subagent's report is second-hand and inadmissible until its claims are shown.                                                                                                                                                                                                                                                | Binds the dispatcher at the instant a synchronous report lands. `SubagentStop` injects only into the worker, never its caller, so it cannot carry this. Async task notifications are not covered: `Notification` is not a canonical event and no handler is registered for it.                                                                         |
| `ida`         | `Stop`                                  | Both                     | `stop_hook_active` checks                      | Advisory quiet gate (`strip_the_reply`, `warn` on both clients): reminds ida to strip its own reply down to load-bearing content before it speaks to the person. Always the same reminder — the hook has no transcript to judge, only that a stop is about to happen. Silent on the continuation stop.                                                             | Registered on `Stop` only, deliberately not `SubagentStop`: `SubagentStop` fires on the _stopping subagent's_ own context, so wiring it there would direct a worker or james to strip a reply it never sends to the person — the defect the superseded `gate-wiring-v07` branch shipped (`plugins/ida/hooks/handlers.py`).                             |
| `pkb`         | `Stop` / `SubagentStop` — **not built** | —                        | —                                              | Nothing today. `plugins/pkb/hooks/handlers.py` registers `UserPromptSubmit` alone and `plugins/pkb/manifest/hooks.template.json` declares no stop event. The intended gate blocks once per stop-chain while the session still holds an `in_progress` task, directing the agent to record its work and release it; the ruling for it is **fail-CLOSED**.            | Work counts only once it is recorded on the task. Blocked on a store-side prerequisite, not on effort: the task API offers no way to ask which tasks a given session holds, and reconstructing that per task is far too slow to run inside a stop hook. Until that exists the gate cannot read the fact it would gate on.                              |
| `rbg`         | `Stop` / `SubagentStop`                 | Both                     | `stop_hook_active` / `background_tasks` checks | Blocks once per stop-chain (`decision: "block"`), directing the agent to invoke the RBG rule checker (`axioms` + project + local rules) and present checkable evidence before stopping. Silent on the continuation stop and while background work runs. Lets the stop through, reporting on stderr, if its message file is missing or empty. Advisory-only on AGY. | **Pillar 4 (Enforcement L2):** Every turn ends with a rule-compliance review; the `stop_hook_active` guard gives once-per-chain semantics with zero state and prevents stop loops. The chain allows one block, so it is not spent on a turn that is not the handback — nor on a block carrying no instruction, which would cost a turn to say nothing. |
| `ts`          | `SessionStart`                          | Claude Code              | `CLAUDE_CODE_REMOTE=true`, `TS_AUTHKEY`        | Launches background `tailscale up` for remote connectivity.                                                                                                                                                                                                                                                                                                        | Enables remote session access over Tailnet.                                                                                                                                                                                                                                                                                                            |
| `ts`          | `SessionEnd`                            | Claude Code              | `TS_SESSION_SYNC_HOST`                         | Transmits session log bundle to remote sync host.                                                                                                                                                                                                                                                                                                                  | Secures session history after termination.                                                                                                                                                                                                                                                                                                             |

`CANONICAL_EVENTS` in [`lib/hooks/dispatch.py`](../lib/hooks/dispatch.py) is exactly the event set this table uses; a client's own wire name is mapped onto it by `TO_CANONICAL`, which is why agy's `PreInvocation` and `PostInvocation` appear here as `UserPromptSubmit` and `Stop`. An event in neither is an event no handler can be registered for.

A handler returns one of three dispositions, in descending order of force, and `_merge` resolves a plugin's handlers by taking the strongest:

- **refusal** — denies a tool call. Reserved for structural impossibility: the session as configured cannot carry the call out, so letting it through produces a hang rather than an outcome. Never a rule verdict.
- **block** — withholds a stop; the turn continues instead. Honoured only on the events in `BLOCKABLE_EVENTS` (`Stop`, `SubagentStop`), and only on Claude Code — agy has no blockable mapped event, and its response contract carries no disposition field, so a block reaches it as an advisory. Returned on any other event it degrades to an advisory and reports the misuse on stderr, so a handler cannot mistake an unhonoured field for enforcement.
- **advisory** — injected context the agent reads and weighs. Everything else.

**Stop hooks are guarded once per chain in the runtime, not in each handler.** A hook that injects on a stop gives the session another turn, which stops again and re-fires it; the client marks that re-entry with `stop_hook_active`. `dispatch.py` drops every handler on a marked `Stop`/`SubagentStop` before any of them load. So a stop hook gets once-per-chain semantics with no state of its own, and a new one cannot ship without the guard by forgetting to write it.

**Two plugins can both register a block on the same client event** — each is a separate hook process, so `_merge`'s precedence is scoped to one plugin's own handler list and never adjudicates between them; the client fires both and each is honoured on its own. Today only `rbg`'s rule-check gate blocks on the face's `Stop`; `pkb`'s task-release gate (Hooks, above) would be the second once it ships.

## Observability & OTEL Tracing

Claude Code's native OpenTelemetry export is the primary tracing mechanism forwarded through a local Tailnet server to GCP:

- **Local Collector Relay:** Session and Polecat container traces send OTLP spans to a local Tailnet OTLP collector endpoint (`OTEL_EXPORTER_OTLP_ENDPOINT`).
- **GCP Export:** The collector relays traces directly to GCP Cloud Trace (`cloudtrace.googleapis.com`) and Cloud Logging.
- **Contract Variables:**
  - `CLAUDE_CODE_ENABLE_TELEMETRY=true`
  - `OTEL_EXPORTER_OTLP_ENDPOINT=http://<tailnet-collector-ip>:4318`
  - `OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf`
  - `OTEL_RESOURCE_ATTRIBUTES=service.name=academicOps,service.version=0.6.0`

The framework forwards this contract into containers and scheduled runs.

Claude Code's native export carries no knowledge of any single plugin's own
internal state — a tool invocation, not a rule evaluated inside `rbg`. Where a
plugin needs its own OTel spans, it builds and exports them itself: `rbg`'s
`evaluator_otel_trace.py` emits one span per rule evaluation (`COPE_EVALUATOR_OTEL_TRACE_PATH`,
plugins/rbg/README.md, "As OTel spans, in OTLP JSON"), as an additional sink
alongside its own JSON Lines trace, using `opentelemetry-sdk` and
`opentelemetry-exporter-otlp-json-file`'s `FileSpanExporter` to write real
OTLP JSON straight to a file path rather than a network endpoint. This
dependency is declared in `plugins/rbg/pyproject.toml` — the first
plugin-owned `pyproject.toml` in the tree, rather than the shared
`templates/plugin/pyproject.template.toml` every other plugin still builds
from — because it is the first plugin whose hooks need a dependency the
generic template does not carry.

## Build

`build/build.py` assembles `dist/<plugin>-<client>` for each plugin and client.

Stages, in order:

1. **Inject.** Copy `lib/` content a plugin declares into the plugin's build
   tree. Declared in the plugin's `manifest/plugin.toml` under `[shared]`.
2. **Resolve includes.** Replace each `@include <path>` line in a markdown file
   with the content of that file from `lib/`. Recursive.
3. **Render manifests.** Merge a `manifest/*.template.json`'s
   `clients.__base__` with its `clients.<client>` section, and write to the
   client's expected path. Every template declares a `manifestVersion` and
   holds its sections under `clients`, keeping the top level for plugin
   identity. A template with no `manifestVersion`, an unrecognised one, or no
   `clients` object fails the build.
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

Real enforcement — a mechanical verdict on whether an agent complied — is a
separate merge-stage check; nothing here reads the transcript or grades the
substance of what an agent did. One mechanism now holds a stop open rather than
merely advising: `rbg`'s rule-check gate (`Stop` / `SubagentStop`, both the face
and a stopping worker) directs the agent to run an explicit rule check and
present evidence before it can stop. `ida`'s quiet gate (`Stop` only,
face-scoped — `SubagentStop` is deliberately not wired, since it fires on a
_stopping subagent's_ own context rather than the face's) is advisory only:
it reminds ida to strip its reply to load-bearing content before it speaks,
but does not hold the stop open. Each is silent on what it finds.

`lib/hooks/dispatch.py` carries a third result kind alongside `warn` and
`refuse` — `block`, which renders as Claude Code's top-level
`{"decision": "block", "reason": ...}` and degrades to the advisory shape on
agy, which has no blockable event — and `is_continuation`, the once-per-stop-
chain guard any such gate needs. One plugin wires it, above (`rbg`); a second
gate on the same primitive, `pkb`'s task-release check, is specified and
still unbuilt (`ARCHITECTURE.md`, Hooks). This section governs: a gate
described anywhere else in this document but absent from a plugin's
`HANDLERS` does not exist.

## Containers

Every plugin works in a fully isolated container: no host paths, no host
credentials, no network assumptions beyond what the environment supplies. The
container receives configuration through the environment only.

Polecat runs asynchronous work in these containers. James dispatches to it.
