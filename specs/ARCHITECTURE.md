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
  aops-core/            pauli, memory, planning, workflow composition, MCP client config; ida — the interactive face.
  orchestrate/          james — the container worker; marsha — QA; adversary;
                        the review skills; the handback hooks.
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

1. **Prompt Situation (`aops-core`):** Ground incoming prompts in strategic PKB history via `UserPromptSubmit` hook + `hydrate`/`brief`.
2. **Workflow Composition (`aops-core`):** Select task-appropriate assurance and review levels (`brief`) matching risk and blast radius. Routing an ask to its template is a separate job — a direct read of [`plugins/aops-core/workflows/INDEX.md`](../plugins/aops-core/workflows/INDEX.md) by whichever agent holds the ask.
3. **Containerized Execution & Dispatch (`ida`):** Dispatch tasks to isolated Docker containers (`lib/polecat`, injected into `ida`, launched by `pc`), writing results back to the PKB task record, committing changes, and pushing.
4. **Dual-Layer Rule Enforcement (`rbg`):** Turn-by-turn local model evaluation of tool calls (`PreToolUse`), plus a stop gate that blocks once per stop-chain and directs the agent to run the RBG rule compliance check (`axioms/` + project + local rules) before stopping (`Stop` / `SubagentStop`).

## Plugins

Directory names are short. `build/marketplace.toml` maps directory →
marketplace name and is the single source of truth for the built plugin set.

| Directory             | Marketplace name | Owns                                                                                                                                                |
| --------------------- | ---------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| `plugins/aops-core`   | `aops-core`      | pauli. Memory, effectual planning, workflow composition, PKB MCP client config; ida, the interactive face, and `strategize`, her own thinking pass. |
| `plugins/orchestrate` | `orchestrate`    | james, the container worker; marsha, QA; adversary; the review skills; the handback hooks; pc, ida's polecat launcher; polecat.                     |
| `plugins/rbg`         | `rbg`            | rbg. Rule enforcement: turn-by-turn evaluator advisory and the stop-side rule gate.                                                                 |
| `plugins/ts`          | `ts`             | Tailscale bring-up for remote sessions.                                                                                                             |
| `plugins/tools`       | `tools`          | Domain research skills.                                                                                                                             |
| `plugins/aops-debug`  | `aops-debug`     | Debug plugin that dumps raw hook payloads.                                                                                                          |

### aops-core

**pauli** is the sole writer to the PKB. No other agent mutates it.

The PKB holds current state, synthesised. Not an append log. Writing to it means
reading what is there, integrating the new fact, and leaving one correct
document.

Workflow composition: the plugin ships a process-template library under
`workflows/`. Pauli composes a workflow for the unit in front of it by reading
templates, matching the required QA assurance level to the task. That happens
inside `brief`, which is the only composer;
[`plugins/aops-core/workflows/INDEX.md`](../plugins/aops-core/workflows/INDEX.md) carries
the routing tree, which any agent reads directly without a skill in between.

The plugin's own `Stop`/`SubagentStop` gate is intended here — while the
session still holds an `in_progress` task, block once per stop-chain and
direct the agent to record its work and release it, fail-CLOSED — but it is
not built, and cannot be until the task store can answer which tasks a given
session holds. What the plugin ships today is ida's `PostToolBatch` quiet
gate (below), not a hook of its own.

### ida

The interactive face, and the only agent that talks to the user. Hosted as an
agent inside `aops-core` (`plugins/aops-core/agents/ida.md`) rather than a plugin of her
own. Academic integrity is non-negotiable. Ida has three jobs and no others:
plan, by commissioning `aops-core:pauli`; launch polecats, through `pc`; and track
what is in flight. She holds between steps and filters what comes back so the
user sees only what needs their judgment. She reaches exactly two agents,
`aops-core:pauli` and `orchestrate:pc`, and nothing else.

**pc** ships from `orchestrate`, because launching containers is how ida gets
work done and nothing else in the framework dispatches on her behalf. Every
polecat runs the `agy` client in a single synchronous execution mode returning
results to stdout. With a task id, the worker writes its result to the task
record and pushes its branch; with a prompt, it returns the output directly to
the caller. Detaching is the wrapping tmux session's job when running outside
an open agent turn. `lib/polecat/` is injected into that plugin
(`plugins/orchestrate/manifest/plugin.toml`) and read as
`${CLAUDE_PLUGIN_ROOT}/polecat/cli.py`.

### orchestrate

Ships **james**, the persona a polecat container boots into
(`lib/polecat/cli.py`, `DEFAULT_AGENT`). He takes one unit of work and sees it
through: hydrate, claim the task, do the work with whatever his harness gives
him, and hand back a report carrying its receipts. How he uses his harness —
subagents, naming, messaging — is his own affair and is not instructed here.
He does not talk to the user.

**adversary** ships alongside him: a red-team reviewer, commissioned when a
claim needs refuting or a plan needs attacking, never scheduled by mandate.

**marsha** judges whether an artifact is outstanding. She runs it. Her `verify`
skill is bound to her and ships alongside her.

She ships here rather than in a plugin of her own, and that is a deliberate
call rather than a consequence of how she is reached. Co-location buys nothing
at dispatch: james reaches `rbg:rbg` and `aops-core:pauli` across plugin boundaries
by namespace, and would reach marsha the same way from anywhere. What decides
it is that `rbg` and `aops-core` exist around infrastructure only their owner needs —
rbg's `PreToolUse` and `Stop` hooks, aops-core's MCP client config — while marsha
carries none: an agent body and one bound skill, no hooks, no config, no
`lib/` injection. A plugin of her own would be a namespace and nothing else, so
she ships with the review machinery that commissions her.

Her independence is unaffected, because it never rested on packaging. It comes
from reviewing blind to the other reviewers and from james treating every
verdict as input rather than truth (`plugins/orchestrate/skills/strategic-review/SKILL.md`).
What packaging does decide is whether she resolves at all: a shipping
instruction naming a reviewer who does not ship leaves the review short-handed
while reading as complete.

**The handback doctrine** — what a returning report must carry, and what its
receiver does with one that carries nothing — is written into each surface that
carries it. The worker's half is
[`plugins/orchestrate/hooks/messages/honesty.md`](../plugins/orchestrate/hooks/messages/honesty.md),
delivered on `Stop` (Hooks, below). The receiver's half reaches an agent through
that agent's own body alone —
[`plugins/aops-core/agents/ida.md`](../plugins/aops-core/agents/ida.md) under "What comes
back", and
[`plugins/orchestrate/agents/james.md`](../plugins/orchestrate/agents/james.md)
under "What you accept".
[`plugins/orchestrate/hooks/messages/hearsay.md`](../plugins/orchestrate/hooks/messages/hearsay.md)
ships, but no registered event delivers it.
The split it encodes is that proof is attached by the **worker**, because a
returning result cannot be amended afterwards, and that the **receiver's** only
move on a report without proof is to send it back. Re-verifying, re-running, or
completing the work on the worker's behalf is not the receiver's job at any
tier. Brief composition is the same shape — the goal and why it matters, the
criteria the output will be assessed against, and the evidence that will be
accepted — and it is stated only in
[`plugins/aops-core/skills/brief/SKILL.md`](../plugins/aops-core/skills/brief/SKILL.md).
James's own body no longer carries it.

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

| Plugin            | Event                                   | Target Client                            | Required Context / Env                                                                                                     | Injected Payload / Action                                                                                                                                                                                                                                                                                                                                                                                                                           | WHY (Purpose & Rationale)                                                                                                                                                                                                                                                                                                                              |
| :---------------- | :-------------------------------------- | :--------------------------------------- | :------------------------------------------------------------------------------------------------------------------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `orchestrate`     | `PostToolBatch`                         | Claude Code                              | none                                                                                                                       | Advisory hearsay reminder (`rule_against_hearsay`, `warn`) carrying `plugins/orchestrate/hooks/messages/hearsay.md`: reminds the dispatcher that a subagent's report is not evidence. Fires when any tool call in the batch was `Agent`.                                                                                                                                                                                                            | Binds the **receiver** at the instant a synchronous report lands, `PostToolBatch` firing once after every call in a batch has resolved so a turn that dispatched several subagents is reminded once rather than once per report.                                                                                                                       |
| `orchestrate`     | `SubagentStart`                         | Claude Code                              | none                                                                                                                       | Advisory reminder (`honest_output`, `warn`) carrying `plugins/orchestrate/hooks/messages/honesty.md`, the evidence contract — every load-bearing conclusion in a report carries falsifiable evidence, quoted verbatim with pinpoint citations, curated to the altitude of the claims the report itself makes rather than every intermediate step. Skipped when `agent_type` is `aops-core:ida`.                                                     | Binds a spawned subagent **worker** at the start of its turn with the honesty and evidence standards.                                                                                                                                                                                                                                                  |
| `aops-core`       | `UserPromptSubmit`                      | Both (Claude Code & AGY)                 | `PKB_MCP_URL`                                                                                                              | Strategic context search instructions & relevant PKB history.                                                                                                                                                                                                                                                                                                                                                                                       | **Pillar 1 (Situation):** Ground every user prompt in historical knowledge and prior decisions before acting.                                                                                                                                                                                                                                          |
| `rbg`             | `PreToolUse`                            | Claude Code                              | `COPE_EVALUATOR_*` (Local LLM model)                                                                                       | Parallel rule compliance advisory with matched rule text & reasoning.                                                                                                                                                                                                                                                                                                                                                                               | **Pillar 4 (Enforcement L1):** Non-blocking, turn-by-turn evaluation of tool calls against active rules via a fast local model.                                                                                                                                                                                                                        |
| `rbg`             | `UserPromptSubmit`                      | AGY (`PreInvocation`)                    | Live rule set files                                                                                                        | Summary roster of active rules for the turn.                                                                                                                                                                                                                                                                                                                                                                                                        | Provides rule visibility on surfaces that lack tool-call interception.                                                                                                                                                                                                                                                                                 |
| `orchestrate`     | `SubagentStop` — **not registered**     | —                                        | —                                                                                                                          | Nothing today. `SubagentStop` is not registered in `HANDLERS`, so a subagent handback reaches no orchestrate handler. `plugins/orchestrate/manifest/hooks.template.json` declares the wire event, so the dispatcher runs and returns nothing.                                                                                                                                                                                                       | The honesty reminder lands on `SubagentStart` instead (above).                                                                                                                                                                                                                                                                                         |
| `orchestrate`     | `UserPromptSubmit`                      | Both (Claude Code; AGY `PreInvocation`)  | `GENAI_ENGINE_API_KEY`, `GENAI_ENGINE_TASK_ID`, `GENAI_ENGINE_TRACE_ENDPOINT`, or an `arthur_config.json` under `.claude/` | Nothing injected. `user_prompt_submit` opens the turn's trace through `claude_code_tracer` and returns `None`.                                                                                                                                                                                                                                                                                                                                      | **Observability.** Plugin-owned OTel spans, distinct from Claude Code's native export. Silent no-op when `discover_config()` finds no configuration, and every tracer handler is wrapped so a failure logs a warning and changes nothing about the turn.                                                                                               |
| `orchestrate`     | `PreToolUse`                            | Claude Code                              | as above                                                                                                                   | Nothing injected. `pre_tool` records the call's start, creating the trace if `UserPromptSubmit` did not. Registered with matcher `*`.                                                                                                                                                                                                                                                                                                               | **Observability.** Opens the span a tool call is measured across.                                                                                                                                                                                                                                                                                      |
| `orchestrate`     | `PostToolUse`                           | Claude Code                              | as above                                                                                                                   | Nothing injected. `post_tool` sends the completed call's `TOOL`/`RETRIEVER`/`AGENT` span. Matcher `*`.                                                                                                                                                                                                                                                                                                                                              | **Observability.** Closes the span with the call's result.                                                                                                                                                                                                                                                                                             |
| `orchestrate`     | `PostToolUseFailure`                    | Claude Code                              | as above                                                                                                                   | Nothing injected. `post_tool_failure` sends an error span for the failed call. Matcher `*`.                                                                                                                                                                                                                                                                                                                                                         | **Observability.** A failed call is a span too; dropping it would leave a trace reading as though the call never happened.                                                                                                                                                                                                                             |
| `orchestrate`     | `Stop`                                  | Both (Claude Code; AGY `PostInvocation`) | as above                                                                                                                   | Nothing injected. `stop` completes the trace and clears the session's tracer state. Declared `async` on Claude Code.                                                                                                                                                                                                                                                                                                                                | **Observability.** The turn's trace is closed at its boundary. Runs on both clients.                                                                                                                                                                                                                                                                   |
| `orchestrate`     | `SessionStart`                          | Claude Code                              | `CLAUDE_ENV_FILE`, `AOPS_BOT_GH_TOKEN`, `AOPS_SESSIONS`, `PKB_MCP_URL`                                                     | Appends the session's credential and path variables to `CLAUDE_ENV_FILE`, scoping git and GitHub auth to the bot token for the session.                                                                                                                                                                                                                                                                                                             | Container and worktree sessions must not inherit the operator's own SSH identity or credential helper. Silent no-op when `CLAUDE_ENV_FILE` is unset.                                                                                                                                                                                                   |
| `aops-core` (ida) | `PostToolBatch`                         | Claude Code                              | none                                                                                                                       | Advisory quiet gate (`be_quiet`, `warn`): reminds ida to strip her own reply down to load-bearing content before she speaks to the person. Fires only when `agent_type` is `aops-core:ida`; every other agent's batch returns nothing. Always the same reminder — the hook has no transcript to judge, only that a batch has resolved. `PostToolBatch` is in `CONTINUATION_EVENTS`, so the dispatcher's self-loop guard keeps it to once per chain. | Fires once after a whole resolved tool batch, so a turn that ran many calls is reminded once rather than once per call. `PostToolBatch` has no agy wire equivalent (`lib/hooks/dispatch.py`), and `aops-core` ships no agy `hooks.json` at all for this gate — so it is Claude-only by construction. See the parity note below the table.              |
| `aops-core`       | `Stop` / `SubagentStop` — **not built** | —                                        | —                                                                                                                          | Nothing today. `plugins/aops-core/hooks/handlers.py` registers `PostToolBatch` (ida's quiet gate) alone and `plugins/aops-core/manifest/hooks.template.json` declares no stop event. The intended gate blocks once per stop-chain while the session still holds an `in_progress` task, directing the agent to record its work and release it; the ruling for it is **fail-CLOSED**.                                                                 | Work counts only once it is recorded on the task. Blocked on a store-side prerequisite: the task API offers no way to ask which tasks a given session holds, and reconstructing that per task is far too slow to run inside a stop hook. Until that exists the gate cannot read the fact it would gate on.                                             |
| `rbg`             | `Stop` / `SubagentStop`                 | Both                                     | `stop_hook_active` / `background_tasks` checks                                                                             | Blocks once per stop-chain (`decision: "block"`), directing the agent to invoke the RBG rule checker (`axioms` + project + local rules) and present checkable evidence before stopping. Silent on the continuation stop and while background work runs. Lets the stop through, reporting on stderr, if its message file is missing or empty. Advisory-only on AGY.                                                                                  | **Pillar 4 (Enforcement L2):** Every turn ends with a rule-compliance review; the `stop_hook_active` guard gives once-per-chain semantics with zero state and prevents stop loops. The chain allows one block, so it is not spent on a turn that is not the handback — nor on a block carrying no instruction, which would cost a turn to say nothing. |
| `ts`              | `SessionStart`                          | Claude Code                              | `CLAUDE_CODE_REMOTE=true`, `TS_AUTHKEY`                                                                                    | Launches background `tailscale up` for remote connectivity.                                                                                                                                                                                                                                                                                                                                                                                         | Enables remote session access over Tailnet.                                                                                                                                                                                                                                                                                                            |
| `ts`              | `SessionEnd`                            | Claude Code                              | `TS_SESSION_SYNC_HOST`                                                                                                     | Transmits session log bundle to remote sync host.                                                                                                                                                                                                                                                                                                                                                                                                   | Secures session history after termination.                                                                                                                                                                                                                                                                                                             |

**ida's quiet gate is Claude-only.** `plugins/aops-core/manifest/hooks.template.json`
registers no `agy` client at all for this gate — `HANDLERS` in
`plugins/aops-core/hooks/handlers.py` registers `PostToolBatch` alone, which has no
agy wire equivalent (`lib/hooks/dispatch.py`). Parity is owed: the gate stays
Claude-only until agy grows a `PostToolBatch` equivalent.

### Hook Output Target & Audience Summary

The recipient audience, delivery timing, and disposition format of each canonical hook event output are summarized below:

| Hook Event                               | Recipient Audience _(Which Agent Sees Output)_                           | Timing / Delivery Moment                                                            | Injected Format & Disposition                                                                          |
| :--------------------------------------- | :----------------------------------------------------------------------- | :---------------------------------------------------------------------------------- | :----------------------------------------------------------------------------------------------------- |
| **`SessionStart`**                       | **Main Session Agent** _(Level 0 Controller)_                            | At session boot, immediately before the first turn / user prompt.                   | `systemMessage` (UI) + `additionalContext` (Agent context). **Advisory**.                              |
| **`UserPromptSubmit`**                   | **Active Prompted Agent** _(Main session controller)_                    | Immediately after prompt submission, before model starts generating.                | `additionalContext` (injected into prompt context). **Advisory**.                                      |
| **`PreToolUse`**                         | **Active Executing Agent** _(Main Agent or Subagent calling tool)_       | Immediately before a tool call is executed by the system.                           | `refusal` (denies tool call) OR `additionalContext` (advisory).                                        |
| **`PostToolUse`**                        | **Active Executing Agent** _(Main Agent or Subagent calling tool)_       | Immediately after an individual tool call finishes.                                 | `additionalContext` (injected into next turn context). **Advisory**.                                   |
| **`PostToolBatch`**                      | **Calling Orchestrator Agent** _(Parent agent that dispatched tools)_    | After an entire batch of parallel tool calls (e.g. `Agent` calls) completes.        | `additionalContext` (injected into calling agent context). **Advisory**.                               |
| **`Stop`**                               | **Active Stopping Agent** _(Main / Top-Level Session Agent)_             | When the main agent finishes generating assistant output and attempts to stop turn. | `decision: "block"` + `reason` (forces turn continuation) OR `additionalContext` (**Advisory**).       |
| **`SubagentStop`** _(Polecat Container)_ | **Stopping Subagent Worker** _(Isolated container / worker process)_     | When an isolated subagent worker finishes its task and attempts to stop.            | `additionalContext` (injected into worker context before handback). **Advisory**.                      |
| **`SubagentStop`** _(Native Task-Tool)_  | **Parent Caller Agent** _(Parent agent that launched the task subagent)_ | When the in-process subagent task finishes and emits its completion notification.   | `additionalContext` (injected into parent caller context via task notification wrapper). **Advisory**. |

`CANONICAL_EVENTS` in [`lib/hooks/dispatch.py`](../lib/hooks/dispatch.py) is exactly the event set this table uses; a client's own wire name is mapped onto it by `TO_CANONICAL`, which is why agy's `PreInvocation` and `PostInvocation` appear here as `UserPromptSubmit` and `Stop`. An event in neither is an event no handler can be registered for.

A handler returns one of three dispositions, in descending order of force, and `_merge` resolves a plugin's handlers by taking the strongest:

- **refusal** — denies a tool call. Reserved for structural impossibility: the session as configured cannot carry the call out, so letting it through produces a hang rather than an outcome. Never a rule verdict.
- **block** — withholds a stop; the turn continues instead. Honoured only on the events in `BLOCKABLE_EVENTS` (`Stop`, `SubagentStop`), and only on Claude Code — agy has no blockable mapped event, and its response contract carries no disposition field, so a block reaches it as an advisory. Returned on any other event it degrades to an advisory and reports the misuse on stderr, so a handler cannot mistake an unhonoured field for enforcement.
- **advisory** — injected context the agent reads and weighs. Everything else.

**Stop hooks are guarded once per chain in the runtime, not in each handler.** A hook that injects on a stop gives the session another turn, which stops again and re-fires it; the client marks that re-entry with `stop_hook_active`. `dispatch.py` drops every handler on a marked `Stop`/`SubagentStop` before any of them load. So a stop hook gets once-per-chain semantics with no state of its own, and a new one cannot ship without the guard by forgetting to write it.

**Two plugins can both register a block on the same client event** — each is a separate hook process, so `_merge`'s precedence is scoped to one plugin's own handler list and never adjudicates between them; the client fires both and each is honoured on its own. When enabled, `rbg`'s rule-check gate blocks on `Stop`/`SubagentStop`; `orchestrate` hooks are advisory (`warn` on `SubagentStart`/`PostToolBatch` and tracer `stop`), and `aops-core`'s task-release gate (Hooks, above) would block once it ships.

## Subagent Dispatch & Inter-Agent Communication

Subagent dispatch and inter-agent messaging operate across containerized execution (`polecat`) and native session agent teams (`Agent`). The routing rules, target parameters, and operational behavior for `SendMessage` are defined below.

### Subagent Dispatch & Inter-Agent Messaging Matrix

| Dispatch / Channel Path                                 | Target Parameter (`to=`)                    | Status          | Operational Mechanics & Observed Constraints                                                                                                                                                                          |
| :------------------------------------------------------ | :------------------------------------------ | :-------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Parent $\rightarrow$ Child Subagent**                 | Child `agentId` (e.g. `af67c74fd42144d3b`)  | **OPERATIONAL** | Parent receives `agentId` in `Agent(...)` tool result and targets child `agentId` directly via `SendMessage`.                                                                                                         |
| **Subagent $\rightarrow$ Main Session**                 | Special reserved alias `"main"`             | **OPERATIONAL** | Subagent calls `SendMessage(to="main")`, which queues the message into the top-level main session's next turn.                                                                                                        |
| **Child $\rightarrow$ Parent via `agentId`**            | Parent `agentId` (e.g. `a9794c3990f98b4c3`) | **OPERATIONAL** | Works when parent explicitly passes its own `agentId` in the prompt brief to the child during dispatch.                                                                                                               |
| **Child $\rightarrow$ Parent via Instance Name**        | Parent's spawn `name` (e.g. `"team-lead"`)  | **OPERATIONAL** | Resolves when the parent was spawned with an explicit `name`. A parent spawned without one has no name to address and must pass its own `agentId` in the brief.                                                       |
| **Subagent $\rightarrow$ Named Peer Agent**             | Peer's instance name (e.g. `"rbg-pr2426"`)  | **OPERATIONAL** | The name is the address. Names keep resolving after the peer completes — a send resumes it from its transcript. Append the `[ref]` shown by `ListAgents` or by an error only to disambiguate two rows sharing a name. |
| **Multi-Tier Return Channel (`L2` $\rightarrow$ `L1`)** | `L1`'s instance name, or its `agentId`      | **CONDITIONAL** | An `L2` subagent is told neither on spawn. Either works once `L1` puts one of them in the brief.                                                                                                                      |

### Operational Constraints & Roster Discovery

1. **Routing Table Address Format:** `SendMessage` addresses an agent **instance** — by the `name` it was spawned with, by the `agentId` from its spawn result, or by the reserved `"main"`. The instance name is the canonical form and keeps resolving after the agent completes. A `subagent_type` is not an address: `"orchestrate:james"` reaches something only if an instance was actually given that name. Spawn any subagent you intend to message with an explicit `name`.
2. **Subagent Return Channel vs. Teammate Naming:** Passing `name` when `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` is enabled converts the spawn into a teammate whose completion notification carries no output. To receive a subagent's result directly in the caller's completion notification turn, omit `name`. Only pass `name` when an agent must be addressable via `SendMessage`.
3. **Tool Granting & Dynamic Discovery:** System error messages from `SendMessage` suggest calling `ListAgents`. However, `ListAgents` is not included in the default subagent tool configuration in standard sessions. Unless explicitly granted in agent configuration, subagents cannot perform dynamic roster lookups.
4. **Hierarchy Briefing Protocol:** A child is told neither its parent's name nor its parent's `agentId` on spawn. An orchestrator dispatching sub-subagents that must report back directly has to put one of the two in the brief.

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
dependency is declared in the shared
`templates/plugin/pyproject.template.toml` — every plugin's `pyproject.toml`
is generated from this template at build time, so `rbg` carries the same
`opentelemetry-sdk` and OTel exporter dependencies as `orchestrate`, whose
`claude_code_tracer.py` and `agy_tracer.py` emit spans to a network endpoint
rather than a file.

## Build

`build/build.py` assembles `dist/<plugin>-<client>` for each plugin and client.

**The size of `dist/` is not a constraint.** It is a regenerable, untracked
artifact, and every plugin gets its own copy of what it needs by design — the
duplication across client trees is the point, not waste. Never trade away an
asset, a bundled library, or any other content because of what it adds to the
output tree, and do not raise dist size as a cost when weighing what to ship.

Stages, in order:

1. **Inject.** Copy `lib/` content a plugin declares into the plugin's build
   tree. Declared in the plugin's `manifest/plugin.toml` under `[shared]`.
2. **Render manifests.** Merge a `manifest/*.template.json`'s
   `clients.__base__` with its `clients.<client>` section, and write to the
   client's expected path. Every template declares a `manifestVersion` and
   holds its sections under `clients`, keeping the top level for plugin
   identity. A template with no `manifestVersion`, an unrecognised one, or no
   `clients` object fails the build.
3. **Adapt to client.** Client adapters in `build/clients/` apply the
   client-specific transformations.
4. **Package.** Tar per client, plus the marketplace manifests.
5. **Cowork channel.** `dist/cowork/` — a directory marketplace assembled from
   the built claude dists: one directory per plugin, a
   `<plugin>-v<version>.zip` upload archive per plugin, and
   `.claude-plugin/marketplace.json` naming the marketplace
   `academicOps-cowork`. Claude-only; skipped when `claude` is not in the
   client list.
6. **OpenClaw channel.** `dist/openclaw/` — a local directory marketplace assembled
   for OpenClaw runtime context: one directory per plugin, a
   `<plugin>-v<version>.zip` archive per plugin, and
   `.claude-plugin/marketplace.json` naming the marketplace
   `academicOps-openclaw`.

### Client adapters

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
- `agents/<name>.md` → validated and adapted for OpenClaw runtime, preserving
  canonical face persona constraints (e.g. `ida`'s narrowed tool surfaces and permissions)
- `axioms/*.md` with `trigger: always_on` → `axioms.jsonl`

`build/clients/agy.py`

- `manifest/plugin.json` → `plugin.json`
- `manifest/hooks.json` → `hooks.json`, script paths unquoted (agy execs via argv)
- `manifest/mcp.json` → `mcp_config.json`
- `commands/<name>.md` → `skills/cmd-<name>/SKILL.md`
- `agents/<name>.md` → `agents/<name>.md`, frontmatter rewritten. An agent's
  `tools:` list is translated into agy's accepted vocabulary through
  [`build/tool_map.toml`](../build/tool_map.toml); `mcp__server__tool` becomes
  `mcp_<server>_<tool>`, and a wildcard collapses to `mcp_<server>_*`. `mcpServers`
  is omitted because agy expects structured server definitions under `mcpServers`
  and drops agents whose frontmatter provides string server names; agy agents access
  MCP tools through workspace-level MCP configs and agy's own implicit
  `call_mcp_tool`, which is granted regardless of `tools:` and so is deliberately
  absent from the vocabulary. `hidden` and `includeSections` are not emitted —
  `test_pauli_agy_frontmatter` in [`tests/test_build.py`](../tests/test_build.py)
  holds the whole shape against pauli's emitted frontmatter. A name starting `mcp_`
  bypasses the accepted-vocabulary check in `build/tools.py`, so a wrong MCP
  name passes the build and fails at agy runtime.

  **The `tools:` key is always emitted, and every name in it must be one agy
  registers.** The two clients assign opposite meanings to an absent `tools:` key:
  Claude Code reads absence as "inherit the full tool pool", agy reads it as
  "restrict to its ten read-only defaults" (`send_message`, `find_by_name`,
  `grep_search`, `view_file`, `list_dir`, `read_url_content`, `search_web`,
  `schedule`, `generate_image`, `manage_task`) — an agent built without the key
  cannot write, run a command, or dispatch a subagent. Omission is therefore never
  a safe translation of "unrestricted": the adapter resolves absence to the full
  accepted vocabulary and emits it. The opposite error is equally fatal — a name
  agy does not register aborts the agent at construction
  (`failed to resolve components: unknown component: tool "<name>" not found in
  registry`), so the vocabulary is the set agy actually registers in the shipped
  image, not every name agy documents. `[provenance]` in `tool_map.toml` records
  the agy version it was extracted against; re-extract when that version moves.
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
gate on the same primitive, `aops-core`'s task-release check, is specified and
still unbuilt (`ARCHITECTURE.md`, Hooks). This section governs: a gate
described anywhere else in this document but absent from a plugin's
`HANDLERS` does not exist.

## Containers

Every plugin works in a fully isolated container: no host paths, no host
credentials, no network assumptions beyond what the environment supplies. The
container receives configuration through the environment only.

Polecat runs asynchronous work in these containers. James dispatches to it.
