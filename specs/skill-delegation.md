---
title: Skill Delegation — Invocation Mechanics and Authority Propagation
type: spec
status: proposed
tier: core
depends_on: [agent-authority, orchestrator-boundary, ultra-vires-enforcer, enforcement]
tags: [spec, agents, skill-delegation, orchestration, authority]
created: 2026-04-23
---

# Skill Delegation — Invocation Mechanics and Authority Propagation

**Status**: Proposed. Authority envelope is owned by [[agent-authority.md]]; this spec
specifies the operational mechanics — how invocation happens at runtime, how context
is passed, how authority flows through nested delegation, and what orchestrators
(james, supervisor, planner) may spawn.

> **Note on location.** The parent task (`task-b3f602c9`) referenced the path
> `aops-core/specs/skill-delegation.md`. The authoritative specs directory is
> `specs/` (top of the monorepo); there is no `aops-core/specs/`. This spec is
> filed at `specs/skill-delegation.md` and indexed from `specs/INDEX.md`.

## Giving Effect

- [[specs/agent-authority.md]] — Authority envelope. This spec refines the invocation side.
- [[specs/orchestrator-boundary.md]] — CLI-agent dispositor rules. Consumes `subagents:` declarations.
- [[specs/ultra-vires-enforcer.md]] — Drift detection. Reads per-invocation context envelopes.
- [[aops-core/agents/*.md]] — All agent files must conform to the invocation contract.
- [[aops-core/skills/*/SKILL.md]] — All skills must declare `allowed-tools` and (new)
  optional `callable-by` / `spawns` hints.

## Problem

`agent-authority.md` establishes **who may call what**. It does not yet specify:

1. **Which invocation mechanism** an agent should use when: the `Skill` tool,
   the `Agent` tool, or a direct prose instruction that inlines a skill
   verbatim. These three paths have different authority, cost, and failure
   semantics, and agents frequently pick the wrong one.
2. **Context-passing contract** — what a caller owes a delegate. Skills and
   sub-agents do not inherit the caller's conversation; they receive only what
   the caller states explicitly in the invocation. Under-briefed delegates fail
   silently or hallucinate context.
3. **Nested delegation rules** — what happens when A spawns B (Agent tool) and
   B invokes skill S. Which allowlist governs S? `agent-authority.md` stated
   the rule tersely ("at every level the controlling envelope is the agent's
   declared allowlists"); this spec works the rule out for the concrete cases.
4. **Orchestrator-specific matrices** — james, supervisor, and planner each
   have distinct orchestration patterns. This spec names what each may spawn
   and what it must pass.
5. **Machine-readable representation** of skill-side delegation metadata, so
   the lint (sibling task `task-8ff8dac0`) can verify symmetry between the
   agent and skill sides.

## Three Invocation Mechanisms

An agent with the appropriate allowlist may cause a skill's instructions to
execute in one of three ways. They differ in authority, context, and
observability.

| Mechanism         | Invocation                                  | Executes in                        | Authority envelope                                                 | Context visibility                              | When to use                                                                   |
| ----------------- | ------------------------------------------- | ---------------------------------- | ------------------------------------------------------------------ | ----------------------------------------------- | ----------------------------------------------------------------------------- |
| **Skill tool**    | `Skill(skill="name", args="...")`           | Caller's own turn                  | `effective(caller) ∩ skill.allowed-tools`                          | Full caller transcript                          | The caller needs the skill's instructions applied in-context, to its own work |
| **Agent tool**    | `Agent(subagent_type="name", prompt="...")` | Fresh sub-agent turn (new context) | `effective(subagent)` — **not** the parent's                       | Only what the parent's prompt states explicitly | The work is independent, deserves its own turn budget, or needs isolation     |
| **Direct prompt** | Agent writes prose instructions inline      | Caller's own turn                  | `effective(caller)` only — the skill's `allowed-tools` is not read | Full caller transcript                          | Only when the skill does not exist as a registered artifact (ad-hoc work)     |

### When each is appropriate

- **Skill tool** is the default for reusable framework behaviour the caller
  wants to perform itself. The skill's instructions temporarily wrap the
  caller's reasoning; the tool set for that wrapped turn is the intersection
  above. If a required skill tool is absent from `effective(caller)`, the
  skill cannot run — the caller must add the tool to its declared `tools:`
  list or pick a different mechanism.

- **Agent tool** is the correct mechanism when the work is logically someone
  else's: independent verification (marsha), compliance review (rbg),
  strategic analysis (pauli), epic-level shepherding (supervisor-as-agent).
  The sub-agent carries its own identity, tools, and turn budget. The parent
  gets back a single result message.

- **Direct prompt** (writing skill-like instructions into the body of the
  current turn, without calling `Skill`) is only appropriate when the
  behaviour is genuinely ad-hoc and has no registered skill. Inlining a
  known skill's instructions this way **bypasses the registry**: the lint
  cannot check referential integrity, and `effective(caller)` is not
  narrowed by `skill.allowed-tools`. Do not do this to "work around"
  a missing allowlist entry — the missing entry is the signal.

### Conversion rules

- If a registered skill exists for the work, the caller MUST invoke it via
  the `Skill` tool (not inline its text). Inlining registered-skill
  instructions is ultra vires: it executes the skill's behaviour without
  its declared tool envelope.
- If a registered agent exists for the work, the caller SHOULD use the
  `Agent` tool rather than inline the agent's persona. Agents are not
  reusable prose — they are authority envelopes.

## Authority Propagation

### The three propagation rules

1. **Spawn does not transit authority.** When A spawns B via `Agent`, B runs
   with `effective(B)`. A's tools, skills, and subagents lists are not
   inherited, extended, or consulted. (Restates agent-authority §Principles
   (4) for completeness.)

2. **Skill invocation narrows authority.** When A invokes S via `Skill`,
   the turn wrapped by S runs with `effective(A) ∩ S.allowed-tools`.
   The intersection can never be larger than `effective(A)`, so invoking
   a skill cannot grant A new tools.

3. **Nested invocation carries the enclosing agent's envelope.** If S
   invokes a further skill S′ (by calling `Skill` in S's instructions),
   the intersection is taken against the **agent** A, not against S:
   `effective(A) ∩ S′.allowed-tools`, and only if `S′ ∈ A.skills`.
   Skills do not form authority chains.

### Nested delegation cases

Let A = caller agent, B = spawned agent, S = skill, S′ = nested skill.

| Path              | Governing envelope                | Required allowlist entries           |
| ----------------- | --------------------------------- | ------------------------------------ |
| A → S             | `effective(A) ∩ S.allowed-tools`  | `S ∈ A.skills`, `Skill ∈ A.tools`    |
| A → S → S′        | `effective(A) ∩ S′.allowed-tools` | `S′ ∈ A.skills`, `Skill ∈ A.tools`   |
| A → B (Agent)     | `effective(B)`                    | `B ∈ A.subagents`, `Agent ∈ A.tools` |
| A → B → S         | `effective(B) ∩ S.allowed-tools`  | `S ∈ B.skills`, `Skill ∈ B.tools`    |
| A → B → C (Agent) | `effective(C)`                    | `C ∈ B.subagents`, `Agent ∈ B.tools` |

**Key invariant**: once an `Agent` boundary is crossed, the parent's allowlists
are irrelevant to the child's further delegation. The child is governed by
its own declared envelope exactly as if invoked directly.

**Corollary**: orchestrators cannot "loan out" tools by spawning an agent
and asking it to perform work the orchestrator itself cannot perform. The
sub-agent either has the tool declared or it does not. There is no
delegation of authority across the spawn boundary.

## Context-Passing Contract

Delegates do not read the caller's transcript. They receive **only** what
the caller writes into the invocation. This is true for `Skill` (the skill's
prompt receives `args`) and for `Agent` (the sub-agent's turn receives the
`prompt` string).

A well-formed invocation includes the following, in the prompt body:

1. **What is being asked.** The concrete deliverable or verdict wanted back.
2. **Why.** Enough rationale for the delegate to make judgment calls within
   its domain rather than asking clarifying questions.
3. **Anchors.** File paths, PR URLs, task IDs, or line numbers the delegate
   will need — not names the caller understands from prior context.
4. **Scope bounds.** What the delegate should NOT do. For reviewers: "report
   findings, do not apply fixes". For decomposers: "file subtasks, do not
   execute them".
5. **Output form.** What format the result should take. A verdict string?
   A file path? A structured block?

Under-briefed delegates hallucinate. Over-briefed delegates ignore the extra
weight and proceed. Err toward explicit.

### Anti-patterns

- **"Based on our conversation, do X."** The delegate has no conversation.
- **"Use the file we discussed."** The delegate knows no files.
- **Handing over tool output blobs verbatim.** If the delegate needs the
  content, state what matters; if it needs the file, give the path.
- **Spawning to avoid briefing.** Spawning does not reduce the briefing
  burden — it relocates it.

## Orchestrator-Specific Matrices

The three principal orchestrators have different scopes and spawn patterns.
Each `subagents:` list is explicit and auditable in the agent's frontmatter;
the table below states current intent. See the authoritative lists in
`aops-core/agents/<name>.md`.

### James — review orchestrator

| Spawns   | Mechanism | When                                               | Must pass                                                       |
| -------- | --------- | -------------------------------------------------- | --------------------------------------------------------------- |
| `rbg`    | Agent     | Always, before synthesis                           | Artifact under review, relevant axiom set                       |
| `pauli`  | Agent     | Strategic artefacts (plans, proposals, specs)      | Artifact, class-of-problem hypothesis, PKB context anchors      |
| `marsha` | Agent     | Runtime-claimable artefacts (code PRs, UI changes) | What was claimed, how to reach it, original acceptance criteria |
| (any)    | Agent     | Re-spawn with refined brief after iteration        | Explicit diff from previous brief — what changed, why           |

Current declaration: `subagents: ["*"]`. This wildcard is an intentional
open declaration for a synthesising role; it is audited rather than
narrowed. James does **not** have execution tools — it produces
recommendations.

**Direct-prompt inlining is forbidden for James's reviewers.** James must
not write "act as Ruth and evaluate…" in prose; it must spawn `rbg` via
`Agent`. Inlining an agent's persona is the single most common
authority-inflation pattern.

### Supervisor — epic orchestrator

| Spawns          | Mechanism | When                                            | Must pass                                                    |
| --------------- | --------- | ----------------------------------------------- | ------------------------------------------------------------ |
| Polecat worker  | `Bash`    | Per subtask, via `polecat run`                  | Task ID; worker hydrates everything else from the task body  |
| `pauli` / `rbg` | Agent     | On integration review, before marking epic done | Epic ID, per-task completion log, open integration questions |

Supervisor's primary delegation mechanism is **polecat dispatch**, not the
`Agent` tool. Polecat workers are registered-agent invocations conducted via
the CLI, not via in-turn spawning. The supervisor's `subagents:` list does
not include polecat workers — polecat is a shell-level boundary with its own
authority model (see `polecat-system.md`).

Supervisor context-passing is unusual: the task body IS the context. The
supervisor writes state to the body and commits before dispatching; the
worker reads its task from the body at startup. This means the
context-passing contract above applies to the **task body**, not to a
per-invocation prompt.

### Planner — graph orchestrator

| Spawns | Mechanism | When | Must pass |
| ------ | --------- | ---- | --------- |
| (none) | —         | —    | —         |

Planner does not spawn sub-agents. It operates on the PKB graph via MCP
tools. Its `subagents:` list is empty by design — decomposition is
read-and-write on the graph, not farmed out.

Planner **does** invoke skills (e.g. `remember` for persistence, internal
planning-mode skills) via the `Skill` tool. Its `skills:` list is the
authoritative enumeration.

### Orchestrator parity rule

An orchestrator may not perform work that its spawn contract forbids by
inlining the persona of an agent it does not list in `subagents:`. If
james did not list `marsha`, it could not satisfy a review need by
writing "act as Marsha and verify…" — the missing allowlist entry is a
structural fact, not a style preference.

## Machine-Readable Representation

### Agent side (existing)

Agent-authority.md already defines `skills:` and `subagents:` in the
agent frontmatter schema. This spec adds no new agent fields.

### Skill side (new optional fields)

Skill frontmatter may declare advisory fields that the lint uses to check
symmetry against the agent side. These are **advisory**: authority is
always governed by the agent's allowlist. Skill-side fields help the
lint catch orphaned or mismatched declarations.

```yaml
# At the top of aops-core/skills/<name>/SKILL.md
allowed-tools: <list<string>>    # REQUIRED. Canonical Claude Code tool names.
callable-by:    <list<string>>   # OPTIONAL. Agent names expected to invoke this skill.
                                 # Lint will warn if an agent lists this skill in
                                 # its skills: but is absent from callable-by,
                                 # and vice versa. Wildcard "*" = any agent.
spawns:         <list<string>>   # OPTIONAL. Nested skills or agents this skill
                                 # may invoke. Used by the lint to propagate
                                 # authority-intersection checks.
mode:           <string>         # OPTIONAL. "iterative" | "conversational" | "batch".
                                 # Affects how the invocation prompt is framed.
```

Example (`aops-core/skills/strategic-review/SKILL.md`):

```yaml
allowed-tools: [Task, Read]
callable-by: [james, pauli]
spawns: []
mode: iterative
```

### Invocation envelope (runtime)

For observability, the ultra-vires enforcer reads a synthetic "invocation
envelope" from each `Skill` or `Agent` tool call:

```yaml
invocation:
  type: skill | agent
  name: <string>           # Skill or agent name
  caller: <agent-name>     # The agent whose turn contains the call
  parent-chain: [a1, a2]   # For nested calls — the chain of enclosing agents
  effective-tools: [...]   # Resolved intersection (skill) or callee's envelope (agent)
  prompt-hash: <sha256>    # Hash of the invocation prompt for replay / audit
```

This envelope is not part of the source files — it is derived at runtime
from the frontmatter and the tool call arguments. It is included here as
the data model the enforcer consumes, so that schema drift can be detected
early.

## Lint Additions

Building on the lint rules in `agent-authority.md §Lint Rules`, this spec
adds:

6. **Skill ↔ agent symmetry.** For every skill `S` and agent `A`:
   - If `S.callable-by` is declared and `A ∈ S.callable-by`, then
     `S ∈ A.skills` MUST hold (error).
   - If `S ∈ A.skills`, then `A ∈ S.callable-by` OR `"*" ∈ S.callable-by`
     SHOULD hold (warn).
7. **Nested-skill reachability.** For every `S′ ∈ S.spawns` where `S′`
   is a skill: every agent `A` with `S ∈ A.skills` must also have
   `S′ ∈ A.skills` (error). Spawning a skill the caller cannot itself
   invoke is an authority-inflation attempt.
8. **Agent-tool parity.** If an agent's body prose instructs it to "use
   the Skill tool" or "spawn via Agent", the corresponding tool
   (`Skill`, `Agent`) MUST appear in `tools:` (error).
9. **Direct-prompt persona detection (heuristic).** Agent body prose that
   contains known agent personas (e.g. "act as Ruth", "as if you were
   Pauli") triggers a warn. Reviewers should either spawn the agent or
   remove the persona reference.

## Migration

Existing agents are compliant with most rules already. Specific migrations:

- **james.md**: `subagents: ["*"]` is retained. Add explanatory note in
  frontmatter or body that the wildcard is intentional open synthesis.
- **pauli.md**: Already correct (`subagents: []`, `skills: [remember,
  planner]`). No change.
- **rbg.md**: Already correct (`skills: []`, `subagents: []`). No change.
- **marsha.md**: Already correct (`skills: [qa]`, `subagents: []`). No change.
- **jr.md**: `skills:` and `subagents:` lists to be audited under the
  sibling lint task; declarations must match any Skill/Agent calls the
  agent actually makes.
- **Skill files**: Adding `callable-by` and `spawns` is a gradual rollout.
  Lint rule 6 is initially `warn` until all skills declare these fields;
  then upgraded to `error`.

## Alignment with Existing Behaviour

This spec intentionally does **not** propose new orchestrator mechanics. The
three propagation rules above formalise behaviour already present in:

- The `Agent` tool surface (spawns open a fresh turn with declared tools).
- The `Skill` tool surface (skill instructions run in-turn, bounded by the
  caller's tool set).
- The ultra-vires enforcer's current narrative-scanning heuristics.

The new contributions are:

- A named taxonomy for the three invocation mechanisms and their trade-offs.
- A context-passing contract with named anti-patterns.
- Concrete spawn matrices for james / supervisor / planner.
- Optional skill-side metadata (`callable-by`, `spawns`) for bidirectional
  lint checks.
- A runtime invocation envelope format for enforcer consumption.

Where this spec disagrees with any existing agent file, the resolution is:
**the spec describes target state**; non-compliant files are migrated via
the sibling lint task. Where it appears to disagree with orchestrator
practice, the agent files are authoritative for current behaviour and the
spec documents the migration path (see §Migration).

## Relation to Other Specs

- **`specs/agent-authority.md`** — Owns the authority envelope and frontmatter
  schema. This spec refines invocation mechanics on top of that envelope.
- **`specs/orchestrator-boundary.md`** — Consumes the orchestrator spawn
  matrices defined here; enforces the CLI-agent-as-dispositor rule.
- **`specs/ultra-vires-enforcer.md`** — Consumes the invocation envelope
  and the direct-prompt-persona heuristic.
- **`specs/plugin-architecture.md`** — Plugin skills follow the same
  delegation contract; `callable-by` may reference plugin-scoped agent
  names.
- **`task-4a6eb501`** (orchestrator boundary enforcement) — Consumes the
  `subagents` allowlist and the §Orchestrator-Specific Matrices tables.
- **`task-d380d98f`** — Parent task. This spec partially discharges its
  authority-plus-delegation work; agent-authority.md owns the authority
  side, this spec owns the delegation side.
- **`task-8ff8dac0`** (lint tooling) — Implements the §Lint Additions here.

## Non-Goals

- **Redefining the authority envelope.** Owned by `agent-authority.md`.
- **Specifying polecat worker dispatch mechanics.** Owned by
  `polecat-system.md` and `non-interactive-agent-workflow-spec.md`.
- **Defining agent personas or prompts.** Persona and knowledge are owned
  by the unification work under `task-1939d819`.
- **Tool-level path permissions.** Enforced by hooks (`policy_enforcer.py`)
  and sandboxes, not by this spec.
- **Hard runtime enforcement.** Layer 5 enforcement is hook-based; this
  spec is L3 (structural declaration) and L4 (lint detection).

## Open Questions

- Should the `Skill` tool narrow `effective(caller)` by intersection
  eagerly at invocation time, or lazily at per-tool-call time? Lazy is
  current behaviour; eager is more explicit but requires harness support.
- Do "direct-prompt persona" violations warrant an error-level lint once
  detection matures, or should they stay at warn given unavoidable false
  positives (e.g. agent bodies that _describe_ another agent without
  _invoking_ it)?
- Should nested `Skill → Agent` (a skill spawning a sub-agent) be
  permitted at all? Current position: allowed, governed by the enclosing
  agent's `subagents:` list. Tighter rule would be to forbid skills from
  calling `Agent` directly and require them to ask the enclosing agent to
  spawn instead. Defer until observed in practice.
