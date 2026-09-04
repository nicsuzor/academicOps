# academicOps Architecture

The authoritative description of what this repository is and how it is built.
Everything here is current state. Nothing here is history.

## Repository layout

```
lib/                    Shared source, never shipped as-is. Most of it is injected
                        into plugin build trees; the rest feeds the image build.
  axioms/               The axioms. Single source of truth.
  hooks/                Hook runtime shared by every plugin that hooks.
  clients/              Shared client-side config fragments.
  py/                   Shared Python helpers.
  kits/                 Docker Sandbox kits: `agy/` and `claude/` supply a
                        client, `aops/` is the mixin that builds and installs the
                        framework inside a sandbox. Injected whole into the
                        plugin that dispatches.
  polecat/              Dispatch-side runtime modules -- the forwarded
                        environment contract (`env_contract.py`), `notify.py`,
                        and `staleness.py` -- injected into that same plugin.
                        `defaults/` holds client config seeds.
build/                  Build system.
templates/              Build-time file templates.
scripts/                Repo tooling, not shipped in any plugin.
plugins/                Plugin sources. Only what a client needs.
  aops/                 pauli, memory, planning, workflow composition, MCP client
                        config; ida -- the interactive face.
  orchestrate/          james -- the container worker; marsha -- QA; adversary;
                        the review skills; the handback hooks.
  rbg/                  rbg -- rule enforcement: an advisory turn-by-turn evaluator
                        plus a stop-side rule-check gate.
  ts/                   Tailscale bring-up.
  tools/                Domain research skills.
  aops-debug/           Debug plugin that dumps raw hook payloads.
plugins.disabled/       Retired sources, excluded from the build.
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

**Loose coupling.** A plugin may depend on `lib/`. A plugin never reads another
plugin's files.

## Core pillars

1. **Prompt situation (`aops`)** -- ground incoming prompts in strategic PKB
   history via `hydrate` / `brief`, invoked directly by the agent. `aops` wires
   no hook for this; its only shipped hook is `PostToolBatch` (`be_quiet`),
   which reminds `ida` to trim her reply, not prompt grounding.
2. **Workflow composition (`aops`)** -- `brief` selects assurance and review
   levels matching risk and blast radius. Routing an ask to its template is a
   separate job: a direct read of templates under `plugins/aops/templates/` by
   whichever agent holds the ask.
3. **Containerised execution and dispatch (`sara`)** -- dispatch tasks to
   isolated Docker Sandboxes, one sandbox and one private git clone per task,
   launched with raw `sbx` from the kits in `lib/kits` (injected into `aops`).
   The worker writes its result back to the PKB task record, commits, and its
   commits are fetched back over the sandbox's own git remote.
4. **Dual-layer rule enforcement (`rbg`)** -- as designed: turn-by-turn
   local-model evaluation of tool calls (`PreToolUse`), plus a stop gate that
   blocks once per stop-chain and directs the agent to run the RBG
   rule-compliance check (`axioms/` + project + local rules) before stopping
   (`Stop` / `SubagentStop`). `plugins/rbg/hooks/handlers.py`'s `HANDLERS` is
   currently empty -- every entry is commented out -- so neither layer is wired
   today.

## Plugins

Directory names are short. `build/marketplace.toml` maps directory →
marketplace name and is the single source of truth for the built plugin set.

| Directory            | Marketplace name | Owns                                                                                                                                                                                                                                        |
| -------------------- | ---------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `plugins/aops`       | `aops`           | pauli (memory, effectual planning, workflow composition, PKB MCP client config); ida (interactive face, strategize); sara (dispatcher) and the `dispatch` skill; james (sandbox worker); marsha (QA); adversary (red-team); handback hooks. |
| `plugins/rbg`        | `rbg`            | rbg. Rule enforcement: turn-by-turn evaluator advisory and the stop-side rule gate.                                                                                                                                                         |
| `plugins/ts`         | `ts`             | Tailscale bring-up for remote sessions.                                                                                                                                                                                                     |
| `plugins/tools`      | `tools`          | Domain research skills.                                                                                                                                                                                                                     |
| `plugins/aops-debug` | `aops-debug`     | Debug plugin that dumps raw hook payloads.                                                                                                                                                                                                  |

### aops

**pauli** is the sole writer to the PKB. No other agent mutates it. The PKB holds
current state, synthesised -- not an append log. Writing to it means reading what
is there, integrating the new fact, and leaving one correct document.

The plugin ships a process-template library under `workflows/`. Pauli composes a
workflow for the unit in front of it by reading templates and matching the
required QA assurance level to the task. That happens inside `brief`, the only
composer.

### ida

The interactive face, and the only agent that talks to the user. Hosted as an
agent inside `aops` ([`plugins/aops/agents/ida.md`](../plugins/aops/agents/ida.md))
rather than a plugin of her own. Academic integrity is non-negotiable. Ida has
three jobs and no others: plan, by commissioning `aops:pauli`; commission
unattended execution, by handing an epic id or a one-line ask to `aops:sara`; and
track what is in flight. She launches nothing herself. She holds between steps
and filters what comes back so the user sees only what needs their judgment.

### sara

The dispatcher, hosted as an agent inside `aops`
([`plugins/aops/agents/sara.md`](../plugins/aops/agents/sara.md)). She takes an
epic from ida and owns every execution mechanic: the epic branch, the wave
sequencing, the sandbox name, kit selection, the model, and the invocation flags.

Dispatch itself is raw `sbx`, and its mechanics live in one skill,
[`plugins/aops/skills/dispatch/SKILL.md`](../plugins/aops/skills/dispatch/SKILL.md):
`sbx create --clone` gives each worker its own sandbox and its own git clone at
the host repository's path, with the host repository mounted read-only at
`/run/sandbox/source`. The clone carries only committed work, so anything a
worker must see is committed and pushed to the epic branch before its sandbox
exists. The kits are the only configuration -- `lib/kits/agy` or `lib/kits/claude`
supplies the client, and the `lib/kits/aops` mixin runs `make install-agy` from
the clone so the framework the worker runs is the one on the branch it is
working. Kit startup is asynchronous and `sbx create` returns before it finishes;
dispatch waits on `/var/log/sbx-kit-startup.log` under an explicit cap. A worker's
commits reach the host through the `sandbox-<name>` git remote, arriving under
`refs/sandboxes/<name>/`, and must be fetched before the sandbox is removed.
[`specs/dispatch/dispatch-system.md`](dispatch/dispatch-system.md) is the design
intent, and carries the open defect: `agy` cannot authenticate inside a sandbox,
which blocks automated `agy` dispatch today.

`lib/kits/` and `lib/polecat/`'s runtime modules are injected into `aops`
(`plugins/aops/manifest/plugin.toml`).

### aops (execution & review)

Ships **james**, the persona a dispatched sandbox worker boots into
([`plugins/aops/agents/james.md`](../plugins/aops/agents/james.md)). He takes one unit of work and sees it
through: hydrate, claim the task, do the work with whatever his harness gives
him, and hand back a report carrying its receipts. How he uses his harness --
subagents, naming, messaging -- is his own affair and is not instructed here. He
does not talk to the user.

**adversary** is a red-team reviewer, commissioned when a claim needs refuting or
a plan needs attacking, never scheduled by mandate.

**marsha** judges whether an artifact is outstanding. She runs it. Her `verify`
skill is bound to her and ships alongside her. She ships here rather than in a
plugin of her own: she carries no hooks, no config and no `lib/` injection, so a
plugin of her own would be a namespace and nothing else. Her independence comes
from reviewing blind to the other reviewers and from james treating every verdict
as input rather than truth
([`plugins/aops/skills/strategic-review/SKILL.md`](../plugins/aops/skills/strategic-review/SKILL.md)),
not from packaging.

**The handback doctrine** -- what a returning report must carry, and what its
receiver does with one that carries nothing -- is written into each surface that
carries it:

- The **worker's** half:
  [`plugins/aops/hooks/messages/honesty.md`](../plugins/aops/hooks/messages/honesty.md),
  delivered on `SubagentStart` (Hooks, below).
- The **receiver's** half reaches an agent through that agent's own body alone --
  [`plugins/aops/agents/ida.md`](../plugins/aops/agents/ida.md) under "What comes
  back", and
  [`plugins/aops/agents/james.md`](../plugins/aops/agents/james.md)
  under "What you accept".
- [`plugins/aops/hooks/messages/hearsay.md`](../plugins/aops/hooks/messages/hearsay.md)
  is delivered on `PostToolBatch`.

Proof is attached by the **worker**, because a returning result cannot be amended
afterwards. The **receiver's** only move on a report without proof is to send it
back; re-verifying, re-running, or completing the work on the worker's behalf is
not the receiver's job at any tier. Brief composition is the same shape -- the
goal and why it matters, the criteria the output will be assessed against, and
the evidence that will be accepted -- and it is stated only in
[`plugins/aops/skills/brief/SKILL.md`](../plugins/aops/skills/brief/SKILL.md).

### rbg

**rbg** judges rule compliance, applying three rule sources in order:

1. `axioms/` shipped in the plugin -- the floor, inviolable
2. `$CWD/.agents/rules/` -- project-local rules
3. `$ACA_DATA/.agents/rules/` -- user-scoped rules from the PKB repo

Later sources add obligations. They never weaken an axiom.

As designed, the plugin advises on the same three sources automatically and
in-session, on a parallel turn-by-turn `PreToolUse` hook running a lightweight
local Reflexes LLM evaluator model, returning `warn` so a flagged call still
proceeds; and a stop-side rule gate, registered alongside `PreToolUse` and
`UserPromptSubmit`, that on `Stop` and `SubagentStop` withholds the stop once
per stop-chain (`block`, `lib/hooks/dispatch.py`), directing the agent to run
the RBG rule-compliance check over the three sources above and present
checkable evidence before it stops. None of this is currently wired:
`plugins/rbg/hooks/handlers.py`'s `HANDLERS` dict is empty, every one of
`evaluate`, `inject_ruleset`, and `rule_check` commented out, marked
`TEMPORARY (2026-08-08, v0.7.1) -- rbg's hooks are deliberately unregistered`.

## Hooks

Every hook is deterministic, lightweight, and single-purpose.

| Plugin       | Event                                                                                   | Client                                                                                                       | Requires                                                                                                                   | Behaviour                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| :----------- | :-------------------------------------------------------------------------------------- | :----------------------------------------------------------------------------------------------------------- | :------------------------------------------------------------------------------------------------------------------------- | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `aops`       | `UserPromptSubmit` (grounding) -- **not built**                                         | --                                                                                                           | --                                                                                                                         | No grounding hook. `plugins/aops/hooks/handlers.py` registers only `user_prompt_submit` / `agy_user_prompt_submit` (tracing, below) and `honest_output` (the evidence contract) on this event; neither reads the PKB. Pillar 1 grounding happens via `hydrate` / `brief`, invoked directly by the agent, not via a hook.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| `aops` (ida) | `PostToolBatch`                                                                         | Claude Code                                                                                                  | none                                                                                                                       | Advisory quiet gate (`be_quiet`, `warn`): reminds ida to strip her reply to load-bearing content before speaking to the person. Fires only when `agent_type` is `aops:ida`. Always the same reminder -- the hook has no transcript to judge, only that a batch resolved. In `CONTINUATION_EVENTS`, so the dispatcher's self-loop guard holds it to once per chain. Claude-only by construction: `PostToolBatch` has no agy wire equivalent and `aops` ships no agy `hooks.json`. Parity is owed.                                                                                                                                                                                                                                                                                                                                               |
| `aops`       | `Stop` / `SubagentStop`                                                                 | `Stop` both; `SubagentStop` Claude Code (agy declares no such event, and a block reaches agy as an advisory) | `plugins/aops/hooks/messages/dump-gate.md`                                                                                 | **Handover gate** (`dump_before_stopping`, `block`): withholds a worker's stop and directs it to run `dump` -- commit, push, release the task, hand over -- because commits and a report are the only things that survive an ephemeral sandbox. Fires only for james, tested affirmatively on `agent_type` ending `:james` or `AOPS_AGENT_NAME` ending `james`, so ida, sara, and a person's own session are never held. Silent while `background_tasks` is non-empty: nothing is being handed back yet, and firing would spend the chain's one block on a turn that is not the handback. Once per stop-chain via `dispatch.py`'s `is_continuation`, not a guard of its own. Fails **open** with a `DEGRADED` line on stderr when `dump-gate.md` is missing or empty -- a block with no instruction costs the agent a turn to be told nothing. |
| `aops`       | `SubagentStart`                                                                         | Claude Code                                                                                                  | none                                                                                                                       | Advisory reminder (`honest_output`, `warn`) carrying `plugins/aops/hooks/messages/honesty.md`, the evidence contract -- every load-bearing conclusion carries falsifiable evidence, quoted verbatim with pinpoint citations, curated to the altitude of the report's own claims. Skipped when `agent_type` is `aops:ida`. Binds a spawned **worker** at the start of its turn.                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| `aops`       | `PostToolBatch`                                                                         | Claude Code                                                                                                  | none                                                                                                                       | Advisory hearsay reminder (`rule_against_hearsay`, `warn`) carrying `plugins/aops/hooks/messages/hearsay.md`: a subagent's report is not evidence. Fires when any tool call in the batch was `Agent`. Binds the **receiver** at the instant a synchronous report lands; `PostToolBatch` fires once after every call in a batch resolves, so a turn that dispatched several subagents is reminded once rather than once per report. Declared `async` on Claude Code.                                                                                                                                                                                                                                                                                                                                                                            |
| `aops`       | `UserPromptSubmit`                                                                      | Both                                                                                                         | `GENAI_ENGINE_API_KEY`, `GENAI_ENGINE_TASK_ID`, `GENAI_ENGINE_TRACE_ENDPOINT`, or an `arthur_config.json` under `.claude/` | **Observability.** Nothing injected. `user_prompt_submit` opens the turn's trace through `claude_code_tracer` and returns `None`. Plugin-owned OTel spans, distinct from Claude Code's native export. Silent no-op when `discover_config()` finds no configuration; every tracer handler is wrapped, so a failure logs a warning and changes nothing about the turn.                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| `aops`       | `PreToolUse`                                                                            | Claude Code                                                                                                  | as above                                                                                                                   | **Observability.** Nothing injected. `pre_tool` records the call's start, creating the trace if `UserPromptSubmit` did not. Matcher `*`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| `aops`       | `PostToolUse`                                                                           | Claude Code                                                                                                  | as above                                                                                                                   | **Observability.** Nothing injected. `post_tool` sends the completed call's `TOOL` / `RETRIEVER` / `AGENT` span. Matcher `*`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| `aops`       | `PostToolUseFailure`                                                                    | Claude Code                                                                                                  | as above                                                                                                                   | **Observability.** Nothing injected. `post_tool_failure` sends an error span. A failed call is a span too; dropping it would leave a trace reading as though the call never happened. Matcher `*`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| `aops`       | `Stop`                                                                                  | Both                                                                                                         | as above                                                                                                                   | **Observability.** Nothing injected. `stop` completes the trace at the turn boundary and clears the session's tracer state.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| `aops`       | `SessionStart`                                                                          | Claude Code                                                                                                  | `CLAUDE_ENV_FILE`, `AOPS_BOT_GH_TOKEN`, `AOPS_SESSIONS`, `PKB_MCP_URL`                                                     | Appends the session's credential and path variables to `CLAUDE_ENV_FILE`, scoping git and GitHub auth to the bot token: container and worktree sessions must not inherit the operator's own SSH identity or credential helper. Silent no-op when `CLAUDE_ENV_FILE` is unset.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| `rbg`        | `PreToolUse` / `UserPromptSubmit` (agy) / `Stop` / `SubagentStop` -- **not registered** | --                                                                                                           | --                                                                                                                         | Nothing today. `plugins/rbg/hooks/handlers.py`'s `HANDLERS` dict is empty -- `evaluate` (layer 1), `inject_ruleset`, and `rule_check` (layer 2, `Stop` / `SubagentStop`) are all commented out, marked `TEMPORARY (2026-08-08, v0.7.1) -- rbg's hooks are deliberately unregistered`. `plugins/rbg/manifest/hooks.template.json` still declares the wire events, so the dispatcher runs and returns nothing, the same shape as the `orchestrate` `SubagentStop` row above. Pillar 4 as designed -- turn-by-turn advisory plus the stop-side rule-check gate -- ships no live hook.                                                                                                                                                                                                                                                             |
| `ts`         | `SessionStart`                                                                          | Claude Code                                                                                                  | `CLAUDE_CODE_REMOTE=true`, `TS_AUTHKEY`                                                                                    | Launches background `tailscale up` for remote session access over the Tailnet.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| `ts`         | `SessionEnd`                                                                            | Claude Code                                                                                                  | `TS_SESSION_SYNC_HOST`                                                                                                     | Transmits the session log bundle to the remote sync host, securing session history after termination.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |

### Events, audiences, and dispositions

`CANONICAL_EVENTS` in [`lib/hooks/dispatch.py`](../lib/hooks/dispatch.py) is
exactly the event set the table above uses; a client's own wire name is mapped
onto it by `TO_CANONICAL`, which is why agy's `PreInvocation` and
`PostInvocation` appear here as `UserPromptSubmit` and `Stop`. An event in
neither is an event no handler can be registered for.

| Event                             | Audience                                      | Timing                                                            | Disposition                                                                                                                 |
| :-------------------------------- | :-------------------------------------------- | :---------------------------------------------------------------- | :-------------------------------------------------------------------------------------------------------------------------- |
| `SessionStart`                    | Main session agent (level 0 controller)       | Session boot, before the first turn                               | `systemMessage` (UI) + `additionalContext` (agent). Advisory.                                                               |
| `UserPromptSubmit`                | Active prompted agent                         | After prompt submission, before generation                        | `additionalContext`. Advisory.                                                                                              |
| `PreToolUse`                      | Active executing agent                        | Immediately before a tool call executes                           | `refusal` (denies the call) **or** `additionalContext` (advisory).                                                          |
| `PostToolUse`                     | Active executing agent                        | Immediately after an individual tool call finishes                | `additionalContext`. Advisory.                                                                                              |
| `PostToolBatch`                   | Calling orchestrator agent                    | After an entire batch of parallel tool calls completes            | `additionalContext` injected into the calling agent. Advisory.                                                              |
| `Stop`                            | Active stopping agent (main / top-level)      | When the main agent finishes output and attempts to stop the turn | `decision: "block"` + `reason` (forces continuation) **or** advisory context.                                               |
| `SubagentStop` (sandbox worker)   | Stopping subagent worker (isolated container) | When an isolated worker finishes and attempts to stop             | `decision: "block"` + `reason` (the handover gate) **or** `additionalContext` injected into worker context before handback. |
| `SubagentStop` (native task tool) | Parent caller agent                           | When the in-process subagent task emits its completion            | `additionalContext` injected into the parent via the task-notification wrapper. Advisory.                                   |

A handler returns one of three dispositions, in descending order of force;
`_merge` resolves a plugin's handlers by taking the strongest:

- **refusal** (`refuse`) -- denies a tool call. Reserved for structural
  impossibility: the session as configured cannot carry the call out, so letting
  it through produces a hang rather than an outcome. Never a rule verdict.
- **block** -- withholds a stop; the turn continues instead. Honoured only on
  `BLOCKABLE_EVENTS` (`Stop`, `SubagentStop`), and only on Claude Code -- agy has
  no blockable mapped event, and its response contract carries no disposition
  field, so a block reaches it as an advisory. Returned on any other event it
  degrades to an advisory and reports the misuse on stderr, so a handler cannot
  mistake an unhonoured field for enforcement.
- **advisory** -- injected context the agent reads and weighs. Everything else.

**Stop hooks are guarded once per chain in the runtime, not in each handler.** A
hook that injects on a stop gives the session another turn, which stops again and
re-fires it; the client marks that re-entry with `stop_hook_active`.
`dispatch.py` drops every handler on a marked `Stop` / `SubagentStop` before any
of them load. A stop hook therefore gets once-per-chain semantics with no state
of its own, and a new one cannot ship without the guard by forgetting to write
it.

**Two plugins can both register a block on the same client event.** Each is a
separate hook process, so `_merge`'s precedence is scoped to one plugin's own
handler list and never adjudicates between them; the client fires both and each
is honoured on its own.

## Subagent dispatch and inter-agent messaging

Dispatch and messaging operate across containerised execution (`polecat`) and
native session agent teams (`Agent`).

| Path                             | Target (`to=`)                             | Status          | Mechanics                                                                                                                                                                                                             |
| :------------------------------- | :----------------------------------------- | :-------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Parent → child subagent          | Child `agentId` (e.g. `af67c74fd42144d3b`) | **OPERATIONAL** | Parent receives `agentId` in the `Agent(...)` tool result and targets it directly.                                                                                                                                    |
| Subagent → main session          | Reserved alias `"main"`                    | **OPERATIONAL** | Queues the message into the top-level main session's next turn.                                                                                                                                                       |
| Child → parent via `agentId`     | Parent `agentId`                           | **OPERATIONAL** | Works when the parent explicitly passes its own `agentId` in the dispatch brief.                                                                                                                                      |
| Child → parent via instance name | Parent's spawn `name` (e.g. `"team-lead"`) | **OPERATIONAL** | Resolves when the parent was spawned with an explicit `name`. A parent spawned without one has no name to address and must pass its own `agentId`.                                                                    |
| Subagent → named peer            | Peer's instance name (e.g. `"rbg-pr2426"`) | **OPERATIONAL** | The name is the address, and keeps resolving after the peer completes -- a send resumes it from its transcript. Append the `[ref]` shown by `ListAgents` or by an error only to disambiguate two rows sharing a name. |
| Multi-tier return (`L2` → `L1`)  | `L1`'s instance name or `agentId`          | **CONDITIONAL** | An `L2` subagent is told neither on spawn. Either works once `L1` puts one of them in the brief.                                                                                                                      |

1. **Addresses are instances.** `SendMessage` addresses an agent **instance** --
   by the `name` it was spawned with, by the `agentId` from its spawn result, or
   by the reserved `"main"`. The instance name is the canonical form and keeps
   resolving after the agent completes. A `subagent_type` is not an address:
   `"orchestrate:james"` reaches something only if an instance was actually given
   that name. Spawn any subagent you intend to message with an explicit `name`.
2. **Naming converts a spawn into a teammate.** Passing `name` when
   `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` is enabled makes the spawn a teammate
   whose completion notification carries no output. To receive a subagent's
   result directly in the caller's completion notification, omit `name`; pass it
   only when the agent must be addressable via `SendMessage`.
3. **Roster discovery is not available by default.** `SendMessage` error
   messages suggest calling `ListAgents`, which is not in the default subagent
   tool configuration. Unless explicitly granted in agent configuration,
   subagents cannot perform dynamic roster lookups.
4. **Hierarchy must be briefed.** A child is told neither its parent's name nor
   its parent's `agentId` on spawn. An orchestrator dispatching sub-subagents
   that must report back directly has to put one of the two in the brief.

## Observability & OTEL Tracing

Claude Code's native OpenTelemetry export is the primary tracing mechanism,
forwarded through a local Tailnet collector to GCP. Session and polecat container
traces send OTLP spans to the collector, which relays them to GCP Cloud Trace
(`cloudtrace.googleapis.com`) and Cloud Logging. The framework forwards this
contract into containers and scheduled runs:

- `CLAUDE_CODE_ENABLE_TELEMETRY=true`
- `OTEL_EXPORTER_OTLP_ENDPOINT=http://<tailnet-collector-ip>:4318`
- `OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf`
- `OTEL_RESOURCE_ATTRIBUTES=service.name=academicOps,service.version=0.6.0`

The native export carries no knowledge of any plugin's internal state -- it sees a
tool invocation, not a rule evaluated inside `rbg`. Where a plugin needs its own
spans it builds and exports them itself. `rbg`'s `evaluator_otel_trace.py` emits
one span per rule evaluation to `COPE_EVALUATOR_OTEL_TRACE_PATH`, as an
additional sink alongside its own JSON Lines trace, using `opentelemetry-sdk` and
`opentelemetry-exporter-otlp-json-file`'s `FileSpanExporter` to write OTLP JSON
to a file path rather than a network endpoint (see
[`plugins/rbg/README.md`](../plugins/rbg/README.md), "As OTel spans, in OTLP
JSON"). The dependency is declared in
`templates/plugin/pyproject.template.toml`, from which every plugin's
`pyproject.toml` is generated at build time, so `rbg` carries the same OTel
dependencies as `orchestrate`, whose `claude_code_tracer.py` and `agy_tracer.py`
export to a network endpoint instead.

## Build

`build/build.py` assembles `dist/<plugin>-<client>` for each plugin and client.

**The size of `dist/` is not a constraint.** It is a regenerable, untracked
artifact, and every plugin gets its own copy of what it needs by design -- the
duplication across client trees is the point, not waste. Never trade away an
asset, a bundled library, or any other content because of what it adds to the
output tree, and do not raise dist size as a cost when weighing what to ship.

Stages, in order:

1. **Inject.** Copy the `lib/` content a plugin declares into its build tree.
   Declared in the plugin's `manifest/plugin.toml` under `[shared]`.
2. **Render manifests.** Merge a `manifest/*.template.json`'s `clients.__base__`
   with its `clients.<client>` section and write to the client's expected path.
   Every template declares a `manifestVersion` and holds its sections under
   `clients`, keeping the top level for plugin identity. A template with no
   `manifestVersion`, an unrecognised one, or no `clients` object fails the
   build.
3. **Adapt to client.** Client adapters in `build/clients/` apply the
   client-specific transformations.
4. **Package.** Tar per client, plus the marketplace manifests.
5. **Cowork channel.** `dist/cowork/` -- a directory marketplace assembled from
   the built claude dists: one directory per plugin, a `<plugin>-v<version>.zip`
   upload archive per plugin, and `.claude-plugin/marketplace.json` naming the
   marketplace `academicOps-cowork`. Claude-only; skipped when `claude` is not in
   the client list.
6. **OpenClaw channel.** `dist/openclaw/` -- a local directory marketplace for the
   OpenClaw runtime context: one directory per plugin, a
   `<plugin>-v<version>.zip` archive per plugin, and
   `.claude-plugin/marketplace.json` naming the marketplace
   `academicOps-openclaw`.

### Client adapters

A client adapter is the only place a client-specific workaround may live. Adding
a plugin requires no change to any adapter.

`build/clients/claude.py`

- `manifest/plugin.json` → `.claude-plugin/plugin.json`
- `manifest/hooks.json` → `hooks/hooks.json` (the only path Claude Code reads)
- `manifest/mcp.json` → `.mcp.json`
- `axioms/*.md` with `trigger: always_on` → `axioms.jsonl`, merged into
  `~/.claude/settings.json` at install time

`build/clients/openclaw.py`

- `manifest/plugin.json` → `.claude-plugin/plugin.json`
- `manifest/hooks.json` → `hooks/hooks.json`
- `manifest/mcp.json` → `.mcp.json`
- `agents/<name>.md` → validated and adapted for the OpenClaw runtime,
  preserving canonical face persona constraints (e.g. `ida`'s narrowed tool
  surfaces and permissions)
- `axioms/*.md` with `trigger: always_on` → `axioms.jsonl`

`build/clients/agy.py`

- `manifest/plugin.json` → `plugin.json`
- `manifest/hooks.json` → `hooks.json`, script paths unquoted (agy execs via
  argv)
- `manifest/mcp.json` → `mcp_config.json`
- `commands/<name>.md` → `skills/cmd-<name>/SKILL.md`
- `agents/<name>.md` → `agents/<name>.md`, frontmatter rewritten
- `axioms/*.md` with `trigger: always_on` → `rules/*.md`

An agent's `tools:` list is translated into agy's accepted vocabulary through
[`build/tool_map.toml`](../build/tool_map.toml); `mcp__server__tool` becomes
`mcp_<server>_<tool>`, and a wildcard collapses to `mcp_<server>_*`. `mcpServers`
is omitted because agy expects structured server definitions there and drops
agents whose frontmatter provides string server names; agy agents reach MCP tools
through workspace-level MCP configs and agy's implicit `call_mcp_tool`, which is
granted regardless of `tools:` and so is deliberately absent from the vocabulary.
`hidden` and `includeSections` are not emitted -- `test_pauli_agy_frontmatter` in
[`tests/test_build.py`](../tests/test_build.py) holds the whole shape against
pauli's emitted frontmatter. A name starting `mcp_` bypasses the
accepted-vocabulary check in `build/tools.py`, so a wrong MCP name passes the
build and fails at agy runtime.

**The `tools:` key is always emitted, and every name in it must be one agy
registers.** The two clients assign opposite meanings to an absent `tools:` key:
Claude Code reads absence as "inherit the full tool pool", agy reads it as
"restrict to its ten read-only defaults" (`send_message`, `find_by_name`,
`grep_search`, `view_file`, `list_dir`, `read_url_content`, `search_web`,
`schedule`, `generate_image`, `manage_task`) -- an agent built without the key
cannot write, run a command, or dispatch a subagent. Omission is therefore never
a safe translation of "unrestricted": the adapter resolves absence to the full
accepted vocabulary and emits it. The opposite error is equally fatal -- a name
agy does not register aborts the agent at construction
(`failed to resolve components: unknown component: tool "<name>" not found in
registry`), so the vocabulary is the set agy actually registers in the shipped
image, not every name agy documents. `[provenance]` in `tool_map.toml` records
the agy version it was extracted against; re-extract when that version moves.

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

Two in-session mechanisms as designed, both advisory:

- `autoMode` -- Claude Code's own classifier, fed the axioms via `axioms.jsonl`
- `cope` -- hook-based rule evaluation

They overlap deliberately. Which one works better is an open question, so both
are meant to ship with neither built as though it were the gate. `cope`
(`rbg`'s `PreToolUse` evaluator, below) is currently unwired, so only `autoMode`
is live today.

Real enforcement -- a mechanical verdict on whether an agent complied -- is a
separate merge-stage check; nothing here reads the transcript or grades the
substance of what an agent did. Two mechanisms hold a stop open rather than
merely advising. `aops`'s handover gate (`dump_before_stopping`, `Stop` /
`SubagentStop`) ships and fires: it withholds a dispatched worker's stop until it
has run `dump`. `rbg`'s rule-check gate, as designed on the same events, directs
the agent to run an explicit rule check and present evidence before it can stop.
`ida`'s quiet gate is advisory only. Each is silent on what it finds.

**This section governs: a gate described anywhere else in this document but
absent from a plugin's `HANDLERS` does not exist.** `lib/hooks/dispatch.py`
carries `block` -- rendered as Claude Code's top-level
`{"decision": "block", "reason": ...}`, degrading to the advisory shape on agy --
and `is_continuation`, the once-per-stop-chain guard any such gate needs. By
this rule, `rbg`'s rule-check gate does not exist today: `HANDLERS` in
`plugins/rbg/hooks/handlers.py` is empty. `aops`'s handover gate is the one gate
built on this primitive -- `dump_before_stopping` is registered on both `Stop`
and `SubagentStop` in `plugins/aops/hooks/handlers.py`.

## Containers

Every plugin works in a fully isolated container: no host paths, no host
credentials, no network assumptions beyond what the environment supplies. The
container receives configuration through the environment only.

Sara dispatches asynchronous work into these containers; james is the worker
that runs inside one.
