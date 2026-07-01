---
created: 2026-04-21
depends_on:
- rbg
- orchestrator-boundary
- enforcement
- plugin-architecture
- polecat-system
id: aops-e8335053
modified: '2026-04-27T22:35:43+00:00'
source: academicOps/specs/agent-authority.md
status: inbox
tags:
- agent-authority
- agents
- framework
- governance
- permissions
- skill-delegation
- spec
tier: core
title: Agent Authority — Permissions and Skill Delegation
type: spec
---

# Agent Authority — Permissions and Skill Delegation

**Status**: Proposed. Audit and lint tooling tracked under `task-d380d98f`.

**Operative state** (per-agent declarations): `aops-core/agents/<name>.md` frontmatter is the SSoT for what tools and permissions each individual agent holds. This spec defines the schema — frontmatter fields, canonical tool naming, the four permissions axes, and skill/sub-agent delegation rules; the per-agent files are the binding declarations against that schema.

**Audit-artifact** (current-state snapshot): `specs/audit/AGENT-TOOLS.md` is the mechanical dump generated from the per-agent frontmatter for at-a-glance comparison. It is not a writeable source — drift is reported by it, not declared in it.

## Giving Effect

- [[rbg]] — Authority envelope that this spec makes concrete (the ultra-vires enforcer's scope, absorbed into the RBG spec during the 2026-07 simplification pass)
- [[orchestrator-boundary]] — CLI orchestrator as a specific authority boundary
- [[enforcement]] — Five-layer enforcement model; this spec feeds L3/L4
- [[polecat-system]] — Enforces `fileAccess` and `bashScopes` at the worktree boundary
- `aops-core/agents` — All agent files must conform
- `.github/agents` — GH Action agent prompts, subset conformance (see §7)

## Problem

Framework agents have evolved organically. Their **permissions** (which tools, servers, bash commands, and file paths they may reach) and **skill delegation** (which skills they may invoke) are implied by prose, by inconsistent YAML frontmatter, and by ad-hoc routing. Tool names appear in at least three styles (`Read`, `read_file`, `mcp_pkb_search`). Some agents declare `skills`, most don't. The ultra-vires enforcer has no machine-readable reference to check against.

The deeper problem is not technical: AI agents are biased toward action. Left alone, they expand scope, take helpful shortcuts, do things adjacent to the task because they seem useful. An agent that writes to a file it wasn't supposed to touch is not a security incident — it's a planning failure. This spec makes the authority envelope explicit, machine-readable, and enforceable, so scope is visible before a task runs, not after.

## Principles

1. **Deny-by-default.** An agent may call only what its frontmatter declares. Anything not listed is denied.
2. **Single source of truth.** Claude Code format is canonical. Other harnesses (Gemini CLI, etc.) are produced by build-time translation.
3. **Skills stay portable.** Skills declare `allowed-tools` as the set the skill needs to function. Skills do not declare which agents may call them — that restriction lives on the agent side.
4. **Authority does not transit by spawning.** When agent A spawns agent B via the `Agent` tool, B runs with B's own declared authority. A does not hand B its tools.
5. **Authority does transit into skills.** When an agent invokes a skill via the `Skill` tool, the skill executes inside the agent's turn and is bounded by the agent's tool allowlist. The skill's `allowed-tools` states what the skill needs; the agent's `tools` states what the agent grants. Effective set = intersection.
6. **Declare intent, then enforce it.** Frontmatter is a public commitment about what an agent does, checked after the fact by the ultra-vires enforcer (L4) and blocked pre-execution by hooks (L5). The declaration is the specification; it is not itself the enforcement.
7. **Four orthogonal axes, independently closed.** Permissions are not one blob. Tools, MCP servers, bash commands, and filesystem paths are four distinct surfaces, each closed by default and opened explicitly. Granting one never implies another.

## Canonical Tool Naming

All agent and skill files use **Claude Code tool names**:

| Category          | Form                                    | Examples                                                                                                                                   |
| ----------------- | --------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| Built-in          | PascalCase                              | `Read`, `Edit`, `Write`, `Bash`, `Grep`, `Glob`, `Agent`, `Skill`, `TodoWrite`, `AskUserQuestion`, `WebFetch`, `WebSearch`, `NotebookEdit` |
| MCP               | `mcp__<server>__<tool>`                 | `mcp__pkb__search`, `mcp__playwright__browser_navigate`                                                                                    |
| Plugin-scoped MCP | `mcp__plugin_<plugin>_<server>__<tool>` | `mcp__plugin_aops-core_pkb__create_task`                                                                                                   |

Legacy snake_case names (`read_file`, `run_shell_command`, `mcp_playwright_browser_navigate`) are **not permitted** in source. The build script (see §7) translates to target-specific forms as needed.

## Agent Frontmatter Schema

Agent files live under `aops-core/agents/<name>.md` (core) or `.github/agents/<name>.agent.md` (GitHub Actions). Frontmatter is YAML. Fields:

### Required

```yaml
name: <string>               # Canonical agent name (matches filename stem)
description: <string>        # One-line routing description (shown to callers)
model: <string>              # "inherit" | "haiku" | "sonnet" | "opus" | concrete id
tools: <list<string>>        # Tool allowlist (canonical names above). Empty list = no tools.
```

### Optional

```yaml
color: <string>              # Display hint; no authority semantics
mcpServers: <list<string>>   # MCP servers the agent may use. Implicitly grants every mcp__<server>__* tool. Use disallowedTools to narrow this set.
disallowedTools: <list<string>>  # Explicit denylist. Overrides grants from `tools` and `mcpServers`.
bashScopes: <list<string>>   # Named command families (e.g. git:read, gh:write, pytest). REQUIRED when `Bash` ∈ tools — see Bash Scopes below.
fileAccess:                  # Repo-relative read/write globs. REQUIRED when any of Read/Write/Edit/NotebookEdit/Glob/Grep ∈ tools — see Filesystem Paths below.
  read: <list<glob>>
  write: <list<glob>>        # optional; omit if no write needed
skills: <list<string>>       # Skill allowlist. If present, agent may invoke only these via the Skill tool. If omitted, no skill invocation is permitted.
subagents: <list<string>>    # Sub-agent allowlist for the Agent tool. If omitted, no subagent spawning is permitted.
permissionMode: <string>     # "default" | "bypassPermissions" | "plan". Default: "default".
maxTurns: <int | false>      # Turn budget. false = unlimited (orchestrator-class only).
effort: <string>             # "low" | "medium" | "high". Advisory only.
background: <bool>           # Default execution mode. Advisory.
isolation: <bool | "worktree">  # Default isolation mode. Advisory.
```

### Deny-by-default grid

| Field             | Omitted means                                              |
| ----------------- | ---------------------------------------------------------- |
| `tools`           | No tool calls permitted                                    |
| `mcpServers`      | No MCP servers                                             |
| `bashScopes`      | No bash — even with `Bash` in `tools`; lint rejects this   |
| `fileAccess`      | No filesystem access — lint rejects if `tools` requires it |
| `skills`          | No skill invocation                                        |
| `subagents`       | No sub-agent spawning                                      |
| `disallowedTools` | No explicit overrides                                      |
| `permissionMode`  | `"default"`                                                |
| `maxTurns`        | Harness default                                            |

### Wildcards

`skills` and `subagents` accept the single-element wildcard list `["*"]` meaning "any installed skill" / "any defined agent". The wildcard is an explicit, auditable declaration — the lint treats `["*"]` as a signal that the agent is intentionally open, not as a missing gate. Tools do not accept a wildcard: the `tools` list is always explicit.

### Effective tool set

```
effective = (tools ∪ expand(mcpServers)) ∖ disallowedTools
```

where `expand(mcpServers)` is every `mcp__<server>__*` tool surfaced by those servers at load time.

## Permissions Model

Four independent axes make up an agent's authority envelope. Each is closed by default; granting one axis does not open another.

### Tools

An agent may call tool `T` iff `T ∈ effective(agent)`. The harness enforces this; RBG (`specs/agents/rbg.md`) detects violations after the fact. Empty `tools` means no calls at all.

### MCP servers

`mcpServers` is a convenience that grants whole-server access — appropriate when an agent genuinely needs an entire server's surface (e.g. the PKB server for research agents). To narrow to specific MCP tools, either:

- Omit `mcpServers` and enumerate in `tools`, or
- Include `mcpServers` and list unwanted tools in `disallowedTools`.

### Bash scopes

`Bash` in `tools` grants the ability to run shell commands — but "which commands" is a separate question, answered by `bashScopes` using named families: `git:read`, `git:write`, `gh:read`, `gh:write`, `pytest`, `ruff`, `fs:read`, `fs:write`, `net:http`, `pkg:install`, `docker`, and so on. Concrete command patterns for each scope live in `aops-core/policies/bash_scopes.toml`.

Named families exist because the permission question at design time is "should a QA agent be able to run tests?", not "should it be able to run `pytest --tb=short -x`?". The patterns are a downstream implementation detail.

**`Bash` without any `bashScopes` is an invalid configuration** — unrestricted shell access violates deny-by-default, and the lint rejects it. The special value `unrestricted` grants any command; it must be declared explicitly, exists only for orchestrator-class agents, and always triggers a lint warning.

### Filesystem paths

`fileAccess` applies when the agent holds any of `Read`, `Write`, `Edit`, `NotebookEdit`, `Glob`, or `Grep`. It declares which repo-relative path globs the agent may read and write:

```yaml
fileAccess:
  read:
    - "**/*"
  write:
    - "aops-core/skills/**"
    - "specs/**"
    - "!specs/archived/**"   # deny override; beats the grant above
```

A `!`-prefixed pattern is an explicit deny and beats any overlapping grant. Symlinks are denied outright — an agent with bash access could otherwise create one inside a granted directory pointing outside the worktree, bypassing the path check.

**Any filesystem tool without `fileAccess` is an invalid configuration**; the lint rejects it. `fileAccess` narrows access _within_ the worktree only — it can never expand beyond it. Paths outside the worktree are categorically denied by the polecat sandbox regardless of what `fileAccess` says. This spec declares the intent; hooks (`policy_enforcer.py`) and the polecat sandbox (`specs/polecat-system.md`) enforce it at the sharp edge.

## Agent Taxonomy and Harness Profiles

The four axes combine into recognisable patterns. These aren't formal types — they're common configurations with different risk profiles, useful for reading an agent file quickly.

- **Read-only analyst**: `Read`, `Glob`, `Grep`, `fileAccess.read` only. No bash, no write, no mutating MCP servers. Can survey and report; cannot change anything. Appropriate for review agents (rbg, Marsha in pure audit mode).
- **PKB-only agent**: `mcpServers: [pkb]`, no bash, no filesystem tools. Reads and writes the knowledge base through the MCP API only. Appropriate for lightweight capture agents.
- **Task executor**: `Read`, `Write`, `Edit`, `Bash` with `git:read`/`git:write`/`gh:write`, plus `fileAccess` scoped to relevant directories. Real work within a bounded scope. Most polecat workers.
- **Orchestrator**: `Agent`, `Skill`, broad tool access, `bashScopes: [unrestricted]` (declared explicitly). Bounded by the spawning rules in Skill Delegation and Sub-agent Delegation below, not by tool restriction. James and the supervisor skill run at this level.

A worker agent with `unrestricted` bash is anomalous; an orchestrator without `Agent` is probably misconfigured.

## Skill Delegation

### Rule

An agent may invoke skill `S` via the `Skill` tool iff:

1. `Skill ∈ effective(agent)` — the agent has the Skill tool itself, and
2. `S ∈ agent.skills` — the skill is on the agent's allowlist.

Skills are portable: they declare `allowed-tools` (what the skill needs), not which agents may call them. An agent invoking a skill temporarily extends its turn with the skill's instructions; the effective tool set for the skill-turn is `effective(agent) ∩ skill.allowed-tools`. If the intersection is empty for a required tool, the skill cannot run — the agent must declare the missing tool or not invoke the skill.

### Nested delegation

A skill may itself declare invocation of further skills or spawn sub-agents — but only if the enclosing agent's `skills` / `subagents` list permits it. Nested invocation does not expand authority; at every level the controlling envelope is the agent's declared allowlists.

### No implicit orchestrator privilege

Orchestrator agents (james, supervisor, planner) have no special spawning rights. Each lists its `subagents` explicitly. "Orchestrator" is a role description, not a permission class.

## Sub-agent Delegation (Agent tool)

An agent may spawn sub-agent `B` via the `Agent` tool iff:

1. `Agent ∈ effective(agent)`, and
2. `B ∈ agent.subagents`.

The sub-agent runs with `B`'s own declared authority. The parent cannot hand the child tools it didn't declare. This is the authority-non-transit rule: spawning is dispatch, not delegation of rights. Delegation is routing, not elevation — a parent that needs broader action routes to an agent that already declares that authority, rather than trying to endow a child with more at runtime. This also keeps permission scope auditable from a single file: to answer "what can this agent do?" you read that agent's frontmatter, never the spawning chain. The only thing that transits from parent to child is the prompt — the context the parent chooses to pass.

## Build Translation

Claude Code frontmatter is the source of truth. Other harnesses receive translated output from `scripts/build.py` (extended under sibling task `task-8ff8dac0`). Translation rules:

| From (Claude Code) | To (Gemini CLI / google-adk) |
| ------------------ | ---------------------------- |
| `Read`             | `read_file`                  |
| `Write`            | `write_file`                 |
| `Edit`             | `replace`                    |
| `Bash`             | `run_shell_command`          |
| `Grep`             | `grep_search`                |
| `Glob`             | `glob`                       |
| `mcp__<s>__<t>`    | `mcp_<s>_<t>` (underscore)   |

Translation is mechanical. Source files are never hand-edited to target form. Target output directories are build artifacts, not committed source.

## Lint Rules

The lint tool (sibling task `task-8ff8dac0`) enforces:

1. **Schema conformance.** All required fields present; no unknown fields.
2. **Canonical naming.** No snake_case tool names in source.
3. **Referential integrity.** Every entry in `tools`, `mcpServers`, `skills`, `subagents` resolves to a real tool / server / skill / agent.
4. **No authority inflation in prose.** Agent body text does not instruct the agent to call tools absent from its allowlist.
5. **Skill `allowed-tools` present.** Every skill file under `aops-core/skills/**/SKILL.md` declares `allowed-tools`.
6. **Bash requires scopes.** `Bash ∈ tools` without `bashScopes` is rejected.
7. **Filesystem tools require fileAccess.** Any of `Read`/`Write`/`Edit`/`NotebookEdit`/`Glob`/`Grep` in `tools` without `fileAccess` is rejected.
8. **`unrestricted` bashScope always warns**, regardless of agent class.

Violations are reported as `error` (1–3, 6, 7 — schema, naming, referential, and axis-completeness violations) or `warn` (4, 5, 8 — prose drift, missing skill metadata, and orchestrator-class exceptions). `error` is a CI blocker; `warn` is surfaced but non-blocking.

## Derived Agents

Some agents exist only as build artifacts for specific runtime targets. They are generated from a canonical source agent by `scripts/build.py` and are not hand-edited.

**`enforcer` (derived from `rbg`).** The enforcer is a compact, haiku-class variant of rbg used by the periodic compliance gate on GitHub targets. It shares rbg's identity and judgment model; the build step narrows its model to `haiku`, trims tools to `Read`, and substitutes a periodic-gate-specific invocation preamble. The current source file `aops-core/agents/enforcer.md` is legacy and will be removed when the build step ships (sibling task `task-8ff8dac0`). Until then, the two files must stay aligned by hand.

## GitHub Action Agents

`.github/agents/*.agent.md` are prompts delivered to GitHub-hosted runs. They have no local frontmatter surface for tool allowlists — tools are granted via `claude_args` in the calling workflow. For this spec they MUST declare at minimum:

```yaml
name: <string>
description: <string>
```

And SHOULD declare (advisory, for audit):

```yaml
tools: <list<string>>        # The claude_args grant set, mirrored here
```

When present, the audit confirms `tools` matches `claude_args` in the invoking workflow.

## Compliance Matrix

Every agent file is audited against this spec. The compliance matrix lives at `specs/agents/agent-compliance-matrix.md` (filed by sibling task `task-8544ef68`). Columns:

- `agent` — file path
- `schema_ok` — all required fields present, no unknown fields
- `naming_ok` — no legacy snake_case tool names
- `referential_ok` — all referenced tools/servers/skills/agents exist
- `skills_declared` — `skills:` present iff the agent invokes `Skill`
- `subagents_declared` — `subagents:` present iff the agent invokes `Agent`
- `notes` — exceptions, rationales, follow-ups

## Relation to the Ultra-Vires Scope

`specs/agents/rbg.md` defines RBG as the post-hoc reviewer that reads session narratives and flags activity outside declared authority. This spec feeds it directly: the agent's frontmatter is the enforcer's ground truth. A call to any tool, server, bash family, or filesystem path outside the declared set is flagged as mechanical overreach.

The permissions layer is declarative; the enforcer is observational. Neither alone is sufficient — a declaration without observation drifts silently, and observation without a declaration has nothing to check drift against.

The enforcement layers, from softest to hardest:

| Layer | Mechanism                      | When it acts        | On violation            |
| ----- | ------------------------------ | ------------------- | ----------------------- |
| L3    | This spec (frontmatter + lint) | At commit / CI      | Lint error              |
| L4    | Ultra-vires enforcer           | Post-session review | Flag, surface, escalate |
| L5    | Policy hooks, polecat sandbox  | Pre-execution       | Hard block              |

> **Funnel / chokepoint pattern.** Least-privilege can be applied not only _negatively_
> (deny what an agent must not touch) but _positively as procedure routing_: deny a
> capability (e.g. `pkb_add`) to **all** agents and grant it to exactly one that must
> invoke a specific skill (e.g. pauli-via-`/planner`). This **chokepoint / funnel** is
> architecturally unforgeable, but it is a **last-resort** enforcement move — it imposes a
> coordination tax on every gated call and relocates assurance onto the chokepoint agent.
> In the [`ENFORCEMENT-MAP.md`](../ENFORCEMENT-MAP.md) pyramid it sits at **L4** (mechanical
> deny), classified under the **Cost axis** as high-coercion / high-recurring-cost. Deploy
> only after cheaper rungs (instruction → deterministic gate → post-hoc ultra-vires
> enforcer) demonstrably fail.
>
> **L-number caution.** The L3/L4/L5 in the table above is a _local_ softest→hardest
> enforcement-layer scheme for this spec. It is **not** the ENFORCEMENT-MAP pyramid L0–L7
> — its "L3" is the frontmatter lint, whereas the pyramid's L3 is voluntary skills. Do not
> cross-reference the two by number.

L5 is the hard edge. A declaration cannot re-open a path that an L5 hook blocks. Conversely, an agent that operates outside its declaration is flagged even if no hook caught it — the declaration is a binding commitment, not a configuration hint.

## Relation to Other Specs

- **`specs/agents/rbg.md`** — RBG reads the declared authority from this spec's frontmatter and flags deviations in session narratives.
- **`specs/future/skill-delegation.md`** — Refines invocation mechanics (Skill / Agent / direct prompt), nested delegation, context-passing contract, and orchestrator spawn matrices on top of this authority envelope.
- **`specs/agents/orchestrator-boundary.md`** — The CLI orchestrator's allow/deny tables are one specific instance of a declared authority envelope.
- **`specs/enforcement/enforcement.md`** — Frontmatter is an L3 (structural) control; the lint is L4 (detection); hooks remain L5 (hard block).
- **`specs/plugins/plugin-architecture.md`** — Plugin agents (when they exist) conform to this same schema; plugin-scoped MCP names follow `mcp__plugin_<plugin>_<server>__<tool>`.
- **`specs/agents/polecat-system.md`** — Enforces `fileAccess` and `bashScopes` at the worktree boundary for remote agent tasks.
- **`task-1939d819`** — Persona/knowledge/authority unification. This spec supplies the _authority_ layer; `task-1939d819` owns persona and knowledge.
- **`task-4a6eb501`** — Orchestrator boundary enforcement. Consumes the `subagents` allowlist, `bashScopes`, and `tools` declared here.
- **`task-b5fec0b5`** — Framework structure formalisation. This spec is one of the structural artifacts it catalogues; that task also owns migrating existing agent files to comply with it.

## Non-Goals

- **Path-level enforcement mechanics.** `fileAccess` declares intent; the polecat sandbox and `policy_enforcer.py` hooks implement the actual enforcement — not in this spec.
- **Rate or quota limits.** Not in this spec — handled by harness budgets.
- **Prompt content review.** Not in this spec — handled by rbg and the enforcer.
- **Per-operation timeouts.** Harness-level concern, independent of the permissions surface.
- **Runtime user approval prompts.** `permissionMode` is a hint to the harness about interactive approval UX, orthogonal to the declarative permissions defined here.
- **Cross-repo permissions.** Each repo's agent files are scoped to that repo; multi-repo coordination happens through the polecat dispatch layer, not permissions extension.

## Open Questions

- Should `subagents` default to `["self"]` (agent may re-spawn itself) or `[]`? Current position: `[]` — explicit declaration always.
- Do we need a `version` field on agent files to manage schema migration? Deferred until lint tooling exists.
- Should skills declare their own `fileAccess` requirements, with the effective grant being the intersection with the calling agent's declaration? Current position: no — skills declare `allowed-tools` for routing; path access is the agent's responsibility. Revisit if agents routinely need broader access than intended because a skill requires it.
- Where should the bash-scope registry live? Current proposal: `aops-core/policies/bash_scopes.toml` (preferred for reviewability) vs. inline in the policy hook.
- When does lint enforcement escalate from warn to error for existing agent files, which predate this spec and lack `bashScopes`/`fileAccess`? Migration tracked under `task-b5fec0b5`.
