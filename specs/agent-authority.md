---
title: Agent Authority — Permissions and Skill Delegation
type: spec
status: proposed
tier: core
depends_on: [ultra-vires-enforcer, orchestrator-boundary, enforcement, plugin-architecture]
tags: [spec, agents, permissions, skill-delegation, governance]
created: 2026-04-21
---

# Agent Authority — Permissions and Skill Delegation

**Status**: Proposed. Audit and lint tooling tracked under `task-d380d98f`.

## Giving Effect

- [[specs/ultra-vires-enforcer.md]] — Authority envelope that this spec makes concrete
- [[specs/orchestrator-boundary.md]] — CLI orchestrator as a specific authority boundary
- [[specs/enforcement.md]] — Five-layer enforcement model; this spec feeds L3/L4
- [[aops-core/agents/]] — All agent files must conform
- [[.github/agents/]] — GH Action agent prompts, subset conformance (see §7)

## Problem

Framework agents have evolved organically. Their **permissions** (which tools they may call) and **skill delegation** (which skills they may invoke) are implied by prose, by inconsistent YAML frontmatter, and by ad-hoc routing. Tool names appear in at least three styles (`Read`, `read_file`, `mcp_pkb_search`). Some agents declare `skills`, most don't. The ultra-vires enforcer has no machine-readable reference to check against.

This spec makes the authority envelope explicit, machine-readable, and enforceable.

## Principles

1. **Deny-by-default.** An agent may call only what its frontmatter declares. Anything not listed is denied.
2. **Single source of truth.** Claude Code format is canonical. Other harnesses (Gemini CLI, etc.) are produced by build-time translation.
3. **Skills stay portable.** Skills declare `allowed-tools` as the set the skill needs to function. Skills do not declare which agents may call them — that restriction lives on the agent side.
4. **Authority does not transit by spawning.** When agent A spawns agent B via the `Agent` tool, B runs with B's own declared authority. A does not hand B its tools.
5. **Authority does transit into skills.** When an agent invokes a skill via the `Skill` tool, the skill executes inside the agent's turn and is bounded by the agent's tool allowlist. The skill's `allowed-tools` states what the skill needs; the agent's `tools` states what the agent grants. Effective set = intersection.

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
skills: <list<string>>       # Skill allowlist. If present, agent may invoke only these via the Skill tool. If omitted, no skill invocation is permitted.
subagents: <list<string>>    # Sub-agent allowlist for the Agent tool. If omitted, no subagent spawning is permitted.
permissionMode: <string>     # "default" | "bypassPermissions" | "plan". Default: "default".
maxTurns: <int | false>      # Turn budget. false = unlimited (orchestrator-class only).
effort: <string>             # "low" | "medium" | "high". Advisory only.
background: <bool>           # Default execution mode. Advisory.
isolation: <bool | "worktree">  # Default isolation mode. Advisory.
```

### Deny-by-default grid

| Field             | Omitted means           |
| ----------------- | ----------------------- |
| `tools`           | No tool calls permitted |
| `mcpServers`      | No MCP servers          |
| `skills`          | No skill invocation     |
| `subagents`       | No sub-agent spawning   |
| `disallowedTools` | No explicit overrides   |
| `permissionMode`  | `"default"`             |
| `maxTurns`        | Harness default         |

### Wildcards

`skills` and `subagents` accept the single-element wildcard list `["*"]` meaning "any installed skill" / "any defined agent". The wildcard is an explicit, auditable declaration — the lint treats `["*"]` as a signal that the agent is intentionally open, not as a missing gate. Tools do not accept a wildcard: the `tools` list is always explicit.

### Effective tool set

```
effective = (tools ∪ expand(mcpServers)) ∖ disallowedTools
```

where `expand(mcpServers)` is every `mcp__<server>__*` tool surfaced by those servers at load time.

## Permissions Model

### Agent ↔ tool

An agent may call tool `T` iff `T ∈ effective(agent)`. The harness enforces this; the ultra-vires enforcer (see `specs/ultra-vires-enforcer.md`) detects violations after the fact.

### Agent ↔ MCP server

`mcpServers` is a convenience that grants whole-server access. To narrow to specific MCP tools, either:

- Omit `mcpServers` and enumerate in `tools`, or
- Include `mcpServers` and list unwanted tools in `disallowedTools`.

### Agent ↔ filesystem and shell

`Bash`, `Read`, `Write`, `Edit` are tools; their presence in `tools` grants general access. Path-level restrictions are **not** part of this spec — they are enforced by hooks (`policy_enforcer.py`) and by the polecat sandbox (`specs/polecat-system.md`). This spec declares intent; hooks enforce the sharp edges.

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

The sub-agent runs with `B`'s own declared authority. The parent cannot hand the child tools it didn't declare. This is the authority-non-transit rule: spawning is dispatch, not delegation of rights.

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

Violations are reported as `error` (schema, naming, referential) or `warn` (prose drift). `error` is a CI blocker; `warn` is surfaced but non-blocking.

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

Every agent file is audited against this spec. The compliance matrix lives at `specs/agent-compliance-matrix.md` (filed by sibling task `task-8544ef68`). Columns:

- `agent` — file path
- `schema_ok` — all required fields present, no unknown fields
- `naming_ok` — no legacy snake_case tool names
- `referential_ok` — all referenced tools/servers/skills/agents exist
- `skills_declared` — `skills:` present iff the agent invokes `Skill`
- `subagents_declared` — `subagents:` present iff the agent invokes `Agent`
- `notes` — exceptions, rationales, follow-ups

## Relation to Other Specs

- **`specs/ultra-vires-enforcer.md`** — The enforcer reads the declared authority from this spec's frontmatter and flags deviations in session narratives.
- **`specs/skill-delegation.md`** — Refines invocation mechanics (Skill / Agent / direct prompt), nested delegation, context-passing contract, and orchestrator spawn matrices on top of this authority envelope.
- **`specs/orchestrator-boundary.md`** — The CLI orchestrator's allow/deny tables are one specific instance of a declared authority envelope.
- **`specs/enforcement.md`** — Frontmatter is an L3 (structural) control; the lint is L4 (detection); hooks remain L5 (hard block).
- **`specs/plugin-architecture.md`** — Plugin agents (when they exist) conform to this same schema; plugin-scoped MCP names follow `mcp__plugin_<plugin>_<server>__<tool>`.
- **`task-1939d819`** — Persona/knowledge/authority unification. This spec supplies the _authority_ layer; `task-1939d819` owns persona and knowledge.
- **`task-4a6eb501`** — Orchestrator boundary enforcement. Consumes the `subagents` allowlist.
- **`task-b5fec0b5`** — Framework structure formalisation. This spec is one of the structural artifacts it catalogues.

## Non-Goals

- **Path-level file permissions.** Not in this spec — handled by hooks and sandboxes.
- **Rate or quota limits.** Not in this spec — handled by harness budgets.
- **Prompt content review.** Not in this spec — handled by rbg and the enforcer.

## Open Questions

- Should `subagents` default to `["self"]` (agent may re-spawn itself) or `[]`? Current position: `[]` — explicit declaration always.
- Do we need a `version` field on agent files to manage schema migration? Deferred until lint tooling exists.
